from __future__ import annotations

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QDate, QEvent, QSettings, QTime, QTimer, Qt, QObject, QThread
# `QKeyEvent` vive en QtGui en PySide6 (no en QtCore); importarlo aquí evita NameError en eventFilter.
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QApplication,
    QAbstractItemView,
    QPlainTextEdit,
    QFrame,
    QHeaderView,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
    QSplitter,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QDialogButtonBox,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
)

from app.application.conflicts_service import ConflictsService
from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases.conflict_resolution_policy import ConflictResolutionPolicy
from app.application.use_cases.retry_sync_use_case import RetrySyncUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.application.use_cases.solicitudes.validaciones import (
    clave_duplicado_solicitud,
    hay_duplicado_distinto,
    validar_seleccion_confirmacion,
)
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.request_time import validate_request_inputs
from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncSummary
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsConfigError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)
from app.ui.conflicts_dialog import ConflictsDialog
from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
from app.ui.person_dialog import PersonaDialog
from app.ui.patterns import apply_modal_behavior, build_modal_actions, status_badge, STATUS_PATTERNS
from app.ui.widgets.toast import ToastManager
from app.ui.controllers.personas_controller import PersonasController
from app.ui.controllers.solicitudes_controller import SolicitudesController, aplicar_confirmacion
from app.ui.controllers.sync_controller import SyncController
from app.ui.controllers.pdf_controller import PdfController
from app.ui.notification_service import ConfirmationSummaryPayload, NotificationService, OperationFeedback
from app.ui.components.saldos_card import SaldosCard
from app.ui.sync_reporting import (
    build_config_incomplete_report,
    build_failed_report,
    build_simulation_report,
    build_sync_report,
    list_sync_history,
    load_sync_report,
    persist_report,
    to_markdown,
)
from app.core.observability import OperationContext, log_event
from app.ui.workers.sincronizacion_workers import PushWorker
from app.bootstrap.logging import log_operational_error
from app.ui.vistas.main_window_health_mixin import MainWindowHealthMixin
from app.ui.vistas.builders.main_window_builders import (
    build_main_window_widgets,
    build_shell_layout,
    build_status_bar,
    create_pages_stack,
    create_sidebar,
    switch_sidebar_page,
    sync_sidebar_state,
)
from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    PDF_PREVIEW_AVAILABLE = True
except ImportError:  # pragma: no cover - depende de instalación local
    QPdfDocument = None
    QPdfView = None
    PDF_PREVIEW_AVAILABLE = False

logger = logging.getLogger(__name__)


def resolve_active_delegada_id(delegada_ids: list[int], preferred_id: object) -> int | None:
    """Devuelve la delegada activa válida a partir del id preferido y la lista cargada."""
    if not delegada_ids:
        return None
    preferred_as_text = str(preferred_id)
    for delegada_id in delegada_ids:
        if str(delegada_id) == preferred_as_text:
            return delegada_id
    return delegada_ids[0]


def _abrir_archivo_local(path: Path) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))



class OptionalConfirmDialog(QDialog):
    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        text = QLabel(message)
        text.setWordWrap(True)
        layout.addWidget(text)

        self.skip_next_check = QCheckBox("No mostrar de nuevo")
        layout.addWidget(self.skip_next_check)

        cancel_button = QPushButton("Cancelar")
        cancel_button.setProperty("variant", "ghost")
        cancel_button.clicked.connect(self.reject)
        ok = QPushButton("Aceptar")
        ok.setProperty("variant", "primary")
        ok.clicked.connect(self.accept)
        layout.addLayout(build_modal_actions(cancel_button, ok))
        apply_modal_behavior(self, primary_button=ok)


class PdfPreviewDialog(QDialog):
    def __init__(self, pdf_generator, default_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pdf_generator = pdf_generator
        self._default_name = default_name
        self._last_pdf_path: Path | None = None
        self._pdf_document = None
        self.setWindowTitle("Previsualización PDF")
        self.resize(920, 680)
        self._build_ui()
        self._generate_preview()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.info_label = QLabel("Genera una vista previa antes de guardar.")
        self.info_label.setProperty("role", "secondary")
        layout.addWidget(self.info_label)

        if PDF_PREVIEW_AVAILABLE and QPdfView and QPdfDocument:
            self._pdf_document = QPdfDocument(self)
            self._pdf_view = QPdfView(self)
            self._pdf_view.setDocument(self._pdf_document)
            layout.addWidget(self._pdf_view, 1)
        else:
            self._pdf_view = QLabel(
                "QPdfView no está disponible en esta instalación.\n"
                "Se abrirá la vista previa con el visor del sistema."
            )
            self._pdf_view.setAlignment(Qt.AlignCenter)
            self._pdf_view.setWordWrap(True)
            self._pdf_view.setProperty("role", "secondary")
            layout.addWidget(self._pdf_view, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)

        refresh = QPushButton("Generar/Actualizar vista")
        refresh.setProperty("variant", "secondary")
        refresh.clicked.connect(self._generate_preview)
        actions.addWidget(refresh)

        save_as = QPushButton("Guardar como…")
        save_as.setProperty("variant", "primary")
        save_as.clicked.connect(self._save_as)
        actions.addWidget(save_as)

        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        apply_modal_behavior(self)

    def _generate_preview(self) -> None:
        with NamedTemporaryFile(prefix="horas_sindicales_", suffix=".pdf", delete=False) as tmp:
            temp_path = Path(tmp.name)
        generated = self._pdf_generator(temp_path)
        self._last_pdf_path = generated
        self.info_label.setText(f"Vista previa lista: {generated.name}")
        if PDF_PREVIEW_AVAILABLE and self._pdf_document is not None:
            self._pdf_document.load(str(generated))
            return
        _abrir_archivo_local(generated)

    def _save_as(self) -> None:
        if self._last_pdf_path is None:
            return
        default_path = str(Path.home() / self._default_name)
        target_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_path, "PDF (*.pdf)")
        if not target_path:
            return
        Path(target_path).write_bytes(self._last_pdf_path.read_bytes())
        self.accept()

    @property
    def exported_path(self) -> Path | None:
        return self._last_pdf_path


class HistoricoDetalleDialog(QDialog):
    def __init__(self, payload: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detalle de solicitud")
        self.resize(560, 420)
        layout = QVBoxLayout(self)

        details = QTextEdit(self)
        details.setReadOnly(True)
        body = "\n".join(f"{key}: {value}" for key, value in payload.items())
        details.setPlainText(body)
        layout.addWidget(details, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        close_button = buttons.button(QDialogButtonBox.Close)
        assert close_button is not None, "QDialogButtonBox.Close debe existir para mantener foco principal"
        apply_modal_behavior(self, primary_button=close_button)


class MainWindow(MainWindowHealthMixin, QMainWindow):
    def __init__(
        self,
        persona_use_cases: PersonaUseCases,
        solicitud_use_cases: SolicitudUseCases,
        grupo_use_cases: GrupoConfigUseCases,
        sheets_service: SheetsService,
        sync_sheets_use_case: SyncSheetsUseCase,
        conflicts_service: ConflictsService,
        health_check_use_case: HealthCheckUseCase | None = None,
        alert_engine: AlertEngine | None = None,
    ) -> None:
        super().__init__()
        self._persona_use_cases = persona_use_cases
        self._solicitud_use_cases = solicitud_use_cases
        self._grupo_use_cases = grupo_use_cases
        self._sheets_service = sheets_service
        self._sync_service = sync_sheets_use_case
        self._conflicts_service = conflicts_service
        self._health_check_use_case = health_check_use_case
        self._alert_engine = alert_engine or AlertEngine()
        self._alert_snooze: dict[str, str] = {}
        self._settings = QSettings("HorasSindicales", "HorasSindicales")
        self._personas: list[PersonaDTO] = []
        self._pending_solicitudes: list[SolicitudDTO] = []
        self._pending_all_solicitudes: list[SolicitudDTO] = []
        self._hidden_pendientes: list[SolicitudDTO] = []
        self._pending_conflict_rows: set[int] = set()
        self._pending_view_all = False
        self._orphan_pendientes: list[SolicitudDTO] = []
        self._sync_in_progress = False
        self._sync_thread: QThread | None = None
        self._sync_worker: PushWorker | None = None
        self._last_sync_report = None
        self._pending_sync_plan: SyncExecutionPlan | None = None
        self._sync_started_at: str | None = None
        self._logs_dir = Path.cwd() / "logs"
        self._retry_sync_use_case = RetrySyncUseCase()
        self._conflict_resolution_policy = ConflictResolutionPolicy(Path.cwd())
        self._sync_attempts: list[dict[str, object]] = []
        self._active_sync_id: str | None = None
        self._attempt_history: tuple[SyncAttemptReport, ...] = ()
        self._field_touched: set[str] = set()
        self._blocking_errors: dict[str, str] = {}
        self._warnings: dict[str, str] = {}
        self._duplicate_target: SolicitudDTO | None = None
        self._preventive_validation_in_progress = False
        self._preventive_validation_debounce_ms = 300
        self._preventive_validation_timer = QTimer(self)
        self._preventive_validation_timer.setSingleShot(True)
        self._preventive_validation_timer.timeout.connect(self._run_preventive_validation)
        self._ui_ready = False
        self.status_sync_label: QLabel | None = None
        self.status_sync_progress: QProgressBar | None = None
        self.status_pending_label: QLabel | None = None
        self.saldos_card: SaldosCard | None = None
        self.horas_input: object | None = None
        self.sidebar: QFrame | None = None
        self.stacked_pages: QStackedWidget | None = None
        self.page_historico: QWidget | None = None
        self.page_configuracion: QWidget | None = None
        self.page_sincronizacion: QWidget | None = None
        self.page_solicitudes: QWidget | None = None
        self.solicitudes_splitter: QSplitter | None = None
        self.sidebar_buttons: list[QPushButton] = []
        self._sidebar_routes: list[dict[str, int | None]] = []
        self._active_sidebar_index = 0
        self.nueva_solicitud_button: QPushButton | None = None
        # Placeholders explícitos para contratos de inicialización self.* en tests estáticos.
        self.main_tabs = None
        self.persona_combo = self.fecha_input = self.desde_input = self.hasta_input = None
        self.desde_container = self.hasta_container = None
        self.desde_placeholder = self.hasta_placeholder = None
        self.completo_check = self.notas_input = None
        self.pending_errors_frame = self.pending_errors_summary = None
        self.solicitud_inline_error = self.delegada_field_error = self.fecha_field_error = self.tramo_field_error = None
        self.primary_cta_button = self.primary_cta_hint = self.insertar_sin_pdf_button = self.confirmar_button = None
        self.agregar_button = self.eliminar_pendiente_button = self.eliminar_huerfana_button = None
        self.revisar_ocultas_button = self.ver_todas_pendientes_button = None
        self.total_pendientes_label = self.pending_filter_warning = None
        self.pendientes_table = self.huerfanas_table = None
        self.pendientes_model = self.huerfanas_model = None
        self.huerfanas_label = None
        self.confirmation_summary_label = self.stepper_context_label = None
        self.stepper_labels = None
        self.sync_button = self.confirm_sync_button = None
        self.retry_failed_button = self.simulate_sync_button = self.review_conflicts_button = None
        self.go_to_sync_config_button = self.copy_sync_report_button = None
        self.sync_progress = self.sync_panel_status = None
        self.sync_status_label = self.sync_status_badge = None
        self.sync_counts_label = self.sync_details_button = None
        self.sync_source_label = self.sync_scope_label = self.sync_idempotency_label = None
        self.last_sync_metrics_label = self.conflicts_reminder_label = self.consequence_microcopy_label = None
        self.historico_search_input = self.historico_estado_combo = self.historico_delegada_combo = None
        self.historico_desde_date = self.historico_hasta_date = None
        self.historico_last_30_button = self.historico_clear_filters_button = None
        self.historico_table = self.historico_model = self.historico_proxy_model = None
        self.historico_empty_state = self.historico_details_button = self.historico_details_content = None
        self.resync_historico_button = self.generar_pdf_button = self.ver_detalle_button = self.eliminar_button = None
        self.editar_pdf_button = self.abrir_pdf_check = self.goto_existing_button = None
        self.total_preview_input = None
        self.add_persona_button = self.edit_persona_button = self.delete_persona_button = None
        self.edit_grupo_button = self.opciones_button = self.config_delegada_combo = None
        self.cuadrante_warning_label = None
        self._last_persona_id: int | None = None
        self._draft_solicitud_por_persona: dict[int, dict[str, object]] = {}
        self.toast = ToastManager()
        self.notifications = NotificationService(self.toast, self)
        self._personas_controller = PersonasController(self)
        self._solicitudes_controller = SolicitudesController(self)
        self._sync_controller = SyncController(self)
        self._pdf_controller = PdfController(self._solicitud_use_cases)
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self._validate_required_widgets()
        self.toast.attach_to(self)
        self._load_personas()
        self._reload_pending_views()
        self._update_global_context()
        self.sync_source_label.setText(f"Fuente: {self._sync_source_text()}")
        self.sync_scope_label.setText(f"Rango: {self._sync_scope_text()}")
        self.sync_idempotency_label.setText("Evita duplicados: misma delegada, fecha y tramo")
        if not self._sync_service.is_configured():
            self._set_config_incomplete_state()
        self._refresh_last_sync_label()
        self._update_sync_button_state()
        self._update_conflicts_reminder()
        self._refresh_health_and_alerts()

    def _validate_required_widgets(self) -> None:
        required_widgets = (
            "persona_combo",
            "fecha_input",
            "desde_input",
            "hasta_input",
            "completo_check",
            "agregar_button",
            "pendientes_table",
            "main_tabs",
            "sync_source_label",
            "sync_scope_label",
            "sync_idempotency_label",
        )
        for widget_name in required_widgets:
            if not hasattr(self, widget_name):
                raise RuntimeError(f"MainWindow mal inicializada. Falta widget requerido: {widget_name}")

    def _create_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setProperty("role", "cardTitle")
        card_layout.addWidget(title_label)

        separator = QFrame()
        separator.setProperty("role", "cardSeparator")
        separator.setFixedHeight(1)
        card_layout.addWidget(separator)
        return card, card_layout

    def _configure_disclosure(
        self,
        button: QPushButton,
        content: QWidget,
        *,
        collapsed_text: str = "Ver detalles",
        expanded_text: str = "Ocultar detalles",
        expandido_por_defecto: bool = False,
    ) -> None:
        button.setCheckable(True)

        def _toggle(checked: bool) -> None:
            content.setVisible(checked)
            button.setText(expanded_text if checked else collapsed_text)

        button.toggled.connect(_toggle)
        _toggle(expandido_por_defecto)
        button.setChecked(expandido_por_defecto)

    def _build_ui(self) -> None:
        self._create_widgets()
        self._build_layout()
        self._wire_signals()
        self._apply_initial_state()
        self._ui_ready = True

    def _build_layout(self) -> None:
        """Mantiene la fase explícita de layout sin alterar el comportamiento actual."""

    def _wire_signals(self) -> None:
        """Mantiene la fase explícita de señales sin alterar el comportamiento actual."""

    def _apply_initial_state(self) -> None:
        """Mantiene la fase explícita de estado inicial sin alterar el comportamiento actual."""

    def _create_widgets(self) -> None:
        build_main_window_widgets(self)

    def _build_shell_layout(self) -> None:
        build_shell_layout(self)


    def _create_sidebar(self) -> QFrame:
        return create_sidebar(self)

    def _create_pages_stack(self) -> QStackedWidget:
        return create_pages_stack(self)

    def _switch_sidebar_page(self, index: int) -> None:
        switch_sidebar_page(self, index)

    def _sync_sidebar_state(self, active_index: int) -> None:
        sync_sidebar_state(self, active_index)

    def _build_status_bar(self) -> None:
        build_status_bar(self)

    def _configure_solicitudes_table(self, table: QTableView) -> None:
        model = table.model()
        column_count = model.columnCount() if model is not None else 6
        if column_count <= 0:
            return
        table.setProperty("role", "dataTable")
        table.setAlternatingRowColors(True)
        header = table.horizontalHeader()
        header.setMinimumSectionSize(78)
        for column in range(max(0, column_count - 1)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(column_count - 1, QHeaderView.Stretch)
        header.setStretchLastSection(False)
        table.setColumnWidth(column_count - 1, 240)
        table.verticalHeader().setDefaultSectionSize(30)
        table.verticalHeader().setVisible(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_responsive_columns()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        # Para juniors: `eventFilter` intercepta eventos antes que el widget objetivo.
        # Si este método lanza una excepción, puede romper incluso el manejador global
        # que muestra QMessageBox de error. Por eso se protege con try/except defensivo.
        # Nota: los eventos de teclado en PySide6 son `QKeyEvent` de `QtGui`.
        try:
            if watched is None or event is None:
                return False
            submit_widgets = {
                getattr(self, "persona_combo", None),
                getattr(self, "fecha_input", None),
                getattr(self, "desde_input", None),
                getattr(self, "hasta_input", None),
                getattr(self, "completo_check", None),
                getattr(self, "notas_input", None),
            }
            if watched in submit_widgets and event.type() == QEvent.KeyPress and isinstance(event, QKeyEvent):
                key_getter = getattr(event, "key", None)
                modifiers_getter = getattr(event, "modifiers", None)
                if not callable(key_getter):
                    return super().eventFilter(watched, event)
                key = key_getter()
                modifiers = modifiers_getter() if callable(modifiers_getter) else Qt.NoModifier
                if key in (Qt.Key_Return, Qt.Key_Enter) and modifiers == Qt.NoModifier:
                    logger.info("ENTER form detected via eventFilter")
                    self._dump_estado_pendientes("enter_form")
                    if self.primary_cta_button.isEnabled():
                        self.primary_cta_button.click()
                    else:
                        logger.info("eventFilter early_return motivo=primary_cta_disabled")
                    return True
            return super().eventFilter(watched, event)
        except Exception:
            logger.exception(
                "event_filter_failed",
                extra={
                    "watched": type(watched).__name__,
                    "event_type": type(event).__name__,
                },
            )
            return False

    def _limpiar_formulario(self) -> None:
        self.fecha_input.setDate(QDate.currentDate())
        self.desde_input.setTime(QTime(9, 0))
        self.hasta_input.setTime(QTime(17, 0))
        self.completo_check.setChecked(False)
        self.notas_input.clear()
        self._field_touched.clear()
        self._blocking_errors.clear()
        self._warnings.clear()
        self.solicitud_inline_error.setVisible(False)
        self.delegada_field_error.setVisible(False)
        self.fecha_field_error.setVisible(False)
        self.tramo_field_error.setVisible(False)
        self._update_solicitud_preview()
        self._update_action_state()
        logger.info("formulario_limpiado")

    def _is_form_dirty(self) -> bool:
        return bool(self.notas_input.toPlainText().strip()) or self.fecha_input.date() != QDate.currentDate() or self.desde_input.time() != QTime(9, 0) or self.hasta_input.time() != QTime(17, 0) or self.completo_check.isChecked()

    def _confirmar_cambio_delegada(self) -> bool:
        respuesta = QMessageBox.question(
            self,
            "Cambiar delegada",
            "Cambiar delegada descartará el formulario actual. ¿Continuar?",
        )
        return respuesta == QMessageBox.StandardButton.Yes

    def _save_current_draft(self, persona_id: int | None) -> None:
        if persona_id is None:
            return
        if not self._is_form_dirty():
            self._draft_solicitud_por_persona.pop(persona_id, None)
            return
        self._draft_solicitud_por_persona[persona_id] = {
            "fecha": self.fecha_input.date(),
            "desde": self.desde_input.time(),
            "hasta": self.hasta_input.time(),
            "completo": self.completo_check.isChecked(),
            "notas": self.notas_input.toPlainText(),
        }

    def _restore_draft_for_persona(self, persona_id: int | None) -> None:
        if persona_id is None:
            return
        draft = self._draft_solicitud_por_persona.get(persona_id)
        if not draft:
            return
        self.fecha_input.setDate(draft["fecha"])
        self.desde_input.setTime(draft["desde"])
        self.hasta_input.setTime(draft["hasta"])
        self.completo_check.setChecked(bool(draft["completo"]))
        self.notas_input.setPlainText(str(draft["notas"]))

    def _update_global_context(self) -> None:
        persona = self._current_persona()
        if self.nueva_solicitud_button is not None:
            self.nueva_solicitud_button.setEnabled(persona is not None)
            self.nueva_solicitud_button.setToolTip("" if persona is not None else "Selecciona delegada")

    def _clear_form(self) -> None:
        """Alias legado: mantener compatibilidad con conexiones antiguas.

        Este método sólo debe tocar estado UI; no ejecuta lógica de negocio.
        Incluye guard clauses para que sea seguro en escenarios de tests donde
        parte de la vista aún no esté completamente inicializada.
        """
        limpiar_formulario = getattr(self, "_limpiar_formulario", None)
        if callable(limpiar_formulario):
            try:
                limpiar_formulario()
            except AttributeError:
                # Fallback defensivo para entornos de inicialización parcial.
                pass

        persona_combo = getattr(self, "persona_combo", None)
        if isinstance(persona_combo, QComboBox):
            persona_combo.setCurrentIndex(-1)

        fecha_input = getattr(self, "fecha_input", None)
        if isinstance(fecha_input, QDateEdit):
            fecha_input.setDate(QDate.currentDate())

        desde_input = getattr(self, "desde_input", None)
        if isinstance(desde_input, QTimeEdit):
            desde_input.setTime(QTime(9, 0))

        hasta_input = getattr(self, "hasta_input", None)
        if isinstance(hasta_input, QTimeEdit):
            hasta_input.setTime(QTime(17, 0))

        completo_check = getattr(self, "completo_check", None)
        if isinstance(completo_check, QCheckBox):
            completo_check.setChecked(False)

        notas_input = getattr(self, "notas_input", None)
        if isinstance(notas_input, QPlainTextEdit):
            notas_input.clear()

        for attr_name in ("_field_touched", "_blocking_errors", "_warnings"):
            state = getattr(self, attr_name, None)
            if hasattr(state, "clear"):
                state.clear()

        for label_name in (
            "solicitud_inline_error",
            "delegada_field_error",
            "fecha_field_error",
            "tramo_field_error",
        ):
            label = getattr(self, label_name, None)
            if isinstance(label, QLabel):
                label.setVisible(False)

        update_preview = getattr(self, "_update_solicitud_preview", None)
        if callable(update_preview):
            update_preview()

        update_actions = getattr(self, "_update_action_state", None)
        if callable(update_actions):
            update_actions()

    def _sincronizar_con_confirmacion(self) -> None:
        result = QMessageBox.question(
            self,
            "Confirmar sincronización",
            "¿Deseas iniciar la sincronización con Google Sheets ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        sync_handler = getattr(self, "_on_sync", None)
        if callable(sync_handler):
            sync_handler()
            return

        logger.error("sync_handler_missing", extra={"handler": "_on_sync"})
        QMessageBox.information(
            self,
            "Sincronización",
            "La sincronización aún no está disponible en esta pantalla.",
        )

    def _on_sync_with_confirmation(self) -> None:
        """Confirma sincronización y delega al controlador/UI workflow existente."""
        result = QMessageBox.question(
            self,
            "Confirmar sincronización",
            "¿Deseas iniciar la sincronización con Google Sheets ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        try:
            if hasattr(self, "_sync_controller") and callable(getattr(self._sync_controller, "on_sync", None)):
                self._sync_controller.on_sync()
                return
            if callable(getattr(self, "_on_sync", None)):
                self._on_sync()
                return
            logger.warning("sync_workflow_not_available")
            QMessageBox.information(
                self,
                "Sincronización",
                "Función no disponible",
            )
        except Exception as exc:  # pragma: no cover - fallback defensivo UI
            log_operational_error(
                logger,
                "Sync failed: no se pudo iniciar desde UI",
                exc=exc,
                extra={"operation": "sync_workflow_start"},
            )
            QMessageBox.critical(self, "Sincronización", f"No se pudo iniciar la sincronización.\n\n{exc}")

    def _on_export_historico_pdf(self) -> None:
        """Alias estable para acciones de shell/header refactorizadas."""
        export_handler = getattr(self, "_on_generar_pdf_historico", None)
        if callable(export_handler):
            export_handler()
            return
        logger.warning("export_historico_pdf_not_available")
        QMessageBox.information(
            self,
            "Exportación",
            "Función no disponible",
        )

    def _normalize_input_heights(self) -> None:
        controls = [
            self.persona_combo,
            self.fecha_input,
            self.desde_input,
            self.hasta_input,
            self.historico_search_input,
            self.historico_estado_combo,
            self.historico_delegada_combo,
            self.historico_desde_date,
            self.historico_hasta_date,
            self.historico_last_30_button,
            self.historico_clear_filters_button,
            self.add_persona_button,
            self.edit_persona_button,
            self.edit_grupo_button,
            self.opciones_button,
            self.delete_persona_button,
            self.agregar_button,
            self.eliminar_pendiente_button,
            self.editar_pdf_button,
            self.insertar_sin_pdf_button,
            self.confirmar_button,
            self.primary_cta_button,
            self.eliminar_button,
            self.ver_detalle_button,
            self.resync_historico_button,
            self.generar_pdf_button,
        ]
        for control in controls:
            control.setMinimumHeight(40)

    def _configure_operativa_focus_order(self) -> None:
        self.setTabOrder(self.persona_combo, self.fecha_input)
        self.setTabOrder(self.fecha_input, self.desde_input)
        self.setTabOrder(self.desde_input, self.hasta_input)
        self.setTabOrder(self.hasta_input, self.completo_check)
        self.setTabOrder(self.completo_check, self.notas_input)
        self.setTabOrder(self.notas_input, self.primary_cta_button)
        self.setTabOrder(self.primary_cta_button, self.insertar_sin_pdf_button)
        self.setTabOrder(self.insertar_sin_pdf_button, self.confirmar_button)

    def _configure_historico_focus_order(self) -> None:
        self.setTabOrder(self.historico_search_input, self.historico_estado_combo)
        self.setTabOrder(self.historico_estado_combo, self.historico_delegada_combo)
        self.setTabOrder(self.historico_delegada_combo, self.historico_desde_date)
        self.setTabOrder(self.historico_desde_date, self.historico_hasta_date)
        self.setTabOrder(self.historico_hasta_date, self.historico_last_30_button)
        self.setTabOrder(self.historico_last_30_button, self.historico_clear_filters_button)
        self.setTabOrder(self.historico_clear_filters_button, self.historico_table)

    def _focus_historico_search(self) -> None:
        self.main_tabs.setCurrentIndex(1)
        self.historico_search_input.setFocus()
        self.historico_search_input.selectAll()

    def _update_responsive_columns(self) -> None:
        if not hasattr(self, "solicitudes_splitter"):
            return
        available_width = self._scroll_area.viewport().width() if hasattr(self, "_scroll_area") else self.width()
        left_size = max(300, int(available_width * 0.4))
        right_size = max(420, int(available_width * 0.6))
        self.solicitudes_splitter.setSizes([left_size, right_size])

    def _load_personas(self, select_id: int | None = None) -> None:
        self.persona_combo.blockSignals(True)
        self.persona_combo.clear()
        self._personas = list(self._persona_use_cases.listar())
        for persona in self._personas:
            self.persona_combo.addItem(persona.nombre, persona.id)
        self.persona_combo.blockSignals(False)

        if select_id is not None:
            for index in range(self.persona_combo.count()):
                if self.persona_combo.itemData(index) == select_id:
                    self.persona_combo.setCurrentIndex(index)
                    break
        self._last_persona_id = self.persona_combo.currentData()
        persona_nombres = {int(persona.id): persona.nombre for persona in self._personas if persona.id is not None}
        self.pendientes_model.set_persona_nombres(persona_nombres)
        self.huerfanas_model.set_persona_nombres(persona_nombres)
        self.historico_model.set_persona_nombres(persona_nombres)
        self.historico_delegada_combo.blockSignals(True)
        self.historico_delegada_combo.clear()
        self.historico_delegada_combo.addItem("Todas", None)
        for persona_id, nombre in sorted(persona_nombres.items(), key=lambda item: item[1].lower()):
            self.historico_delegada_combo.addItem(nombre, persona_id)
        self.historico_delegada_combo.blockSignals(False)
        self.config_delegada_combo.blockSignals(True)
        self.config_delegada_combo.clear()
        sorted_personas = sorted(persona_nombres.items(), key=lambda item: item[1].lower())
        for persona_id, nombre in sorted_personas:
            # Nunca usar el texto visible para identificar registros: puede repetirse.
            # Usamos siempre persona_id (delegada_id real) en userData.
            self.config_delegada_combo.addItem(nombre, persona_id)
        delegada_ids = [persona_id for persona_id, _nombre in sorted_personas]
        preferred_id = select_id if select_id is not None else self._settings.value("contexto/delegada_seleccionada_id", None)
        active_id = resolve_active_delegada_id(delegada_ids, preferred_id)
        if active_id is not None:
            for index in range(self.config_delegada_combo.count()):
                if self.config_delegada_combo.itemData(index) == active_id:
                    self.config_delegada_combo.setCurrentIndex(index)
                    break
        self.config_delegada_combo.blockSignals(False)
        self._sync_config_persona_actions()
        self._on_persona_changed()

    def _current_persona(self) -> PersonaDTO | None:
        index = self.persona_combo.currentIndex()
        if index < 0:
            return None
        persona_id = self.persona_combo.currentData()
        for persona in self._personas:
            if persona.id == persona_id:
                return persona
        return None

    def _on_persona_changed(self, *_args) -> None:
        nueva_persona_id = self.persona_combo.currentData()

        if self._last_persona_id != nueva_persona_id and self._is_form_dirty() and not self._confirmar_cambio_delegada():
            for index in range(self.persona_combo.count()):
                if self.persona_combo.itemData(index) == self._last_persona_id:
                    self.persona_combo.setCurrentIndex(index)
                    break
            return

        if self._last_persona_id != nueva_persona_id:
            self._save_current_draft(self._last_persona_id)
            self._limpiar_formulario()
            self._restore_draft_for_persona(nueva_persona_id)

        self._last_persona_id = nueva_persona_id
        self.pendientes_table.clearSelection()
        self.huerfanas_table.clearSelection()
        self._reload_pending_views()
        self._update_action_state()
        self._refresh_saldos()
        self._update_solicitud_preview()
        self._update_global_context()

    def _on_config_delegada_changed(self, *_args) -> None:
        persona_id = self.config_delegada_combo.currentData()
        self._sync_config_persona_actions()
        self._settings.setValue("contexto/delegada_activa", persona_id)
        self._settings.setValue("contexto/delegada_seleccionada_id", persona_id)
        if persona_id is None:
            return
        for index in range(self.persona_combo.count()):
            if self.persona_combo.itemData(index) == persona_id:
                self.persona_combo.setCurrentIndex(index)
                break

    def _restaurar_contexto_guardado(self) -> None:
        delegada_id = self._settings.value("contexto/delegada_seleccionada_id", None)
        historico_id = self._settings.value("historico/delegada", None)
        for combo, value in ((self.config_delegada_combo, delegada_id), (self.historico_delegada_combo, historico_id)):
            for index in range(combo.count()):
                if str(combo.itemData(index)) == str(value):
                    combo.setCurrentIndex(index)
                    break

    def _selected_config_persona(self) -> PersonaDTO | None:
        persona_id = self.config_delegada_combo.currentData()
        if persona_id is None:
            return None
        for persona in self._personas:
            if persona.id == persona_id:
                return persona
        return None

    def _sync_config_persona_actions(self) -> None:
        has_selected_persona = self.config_delegada_combo.currentData() is not None
        self.edit_persona_button.setEnabled(has_selected_persona)
        self.delete_persona_button.setEnabled(has_selected_persona)

    def _apply_historico_text_filter(self) -> None:
        self.historico_proxy_model.set_search_text(self.historico_search_input.text())
        self._update_action_state()

    def _apply_historico_filters(self) -> None:
        self.historico_proxy_model.set_date_range(self.historico_desde_date.date(), self.historico_hasta_date.date())
        self.historico_proxy_model.set_estado_code(self.historico_estado_combo.currentData())
        delegada_id = self.historico_delegada_combo.currentData()
        self.historico_proxy_model.set_delegada_id(delegada_id)
        self._settings.setValue("historico/delegada", delegada_id)
        self._apply_historico_text_filter()
        self._update_historico_empty_state()


    def _update_historico_empty_state(self) -> None:
        has_rows = self.historico_proxy_model.rowCount() > 0
        self.historico_empty_state.setVisible(not has_rows)
        self.historico_details_button.setVisible(has_rows)
        self.historico_details_content.setVisible(has_rows and self.historico_details_button.isChecked())

    def _apply_historico_last_30_days(self) -> None:
        self.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
        self.historico_hasta_date.setDate(QDate.currentDate())
        self._apply_historico_filters()

    def _clear_historico_filters(self) -> None:
        self.historico_search_input.clear()
        self.historico_estado_combo.setCurrentIndex(0)
        self.historico_delegada_combo.setCurrentIndex(0)
        self._apply_historico_last_30_days()

    def _on_historico_escape(self) -> None:
        if self.historico_search_input.hasFocus():
            self.historico_search_input.clearFocus()
            return
        self.historico_table.clearSelection()

    def _on_completo_changed(self, checked: bool) -> None:
        self._sync_completo_visibility(checked)
        self._update_solicitud_preview()

    def _on_fecha_changed(self) -> None:
        if self.completo_check.isChecked():
            self.completo_check.setChecked(False)
        self._update_solicitud_preview()

    def _configure_time_placeholders(self) -> None:
        self.desde_placeholder.setVisible(False)
        self.hasta_placeholder.setVisible(False)
        desde_hint = self.desde_container.sizeHint()
        hasta_hint = self.hasta_container.sizeHint()
        self.desde_placeholder.setFixedSize(desde_hint)
        self.hasta_placeholder.setFixedSize(hasta_hint)
        self._sync_completo_visibility(self.completo_check.isChecked())
        self._bind_manual_hours_preview_refresh()

    def _bind_preventive_validation_events(self) -> None:
        self.persona_combo.currentIndexChanged.connect(lambda _: self._mark_field_touched("delegada"))
        self.fecha_input.editingFinished.connect(lambda: self._mark_field_touched("fecha"))
        self.desde_input.editingFinished.connect(lambda: self._mark_field_touched("tramo"))
        self.hasta_input.editingFinished.connect(lambda: self._mark_field_touched("tramo"))
        self.completo_check.toggled.connect(lambda _: self._mark_field_touched("tramo"))

    def _mark_field_touched(self, field: str) -> None:
        self._field_touched.add(field)
        self._schedule_preventive_validation()

    def _schedule_preventive_validation(self) -> None:
        if self._preventive_validation_in_progress:
            return
        self._preventive_validation_timer.start(self._preventive_validation_debounce_ms)

    def _run_preventive_validation(self) -> None:
        if self._preventive_validation_in_progress:
            return
        self._preventive_validation_in_progress = True
        try:
            blocking, warnings = self._collect_preventive_validation()
            self._blocking_errors = blocking
            self._warnings = warnings
            self._render_preventive_validation()
            self._dump_estado_pendientes("after_run_preventive_validation")
        finally:
            self._preventive_validation_in_progress = False

    def _collect_base_preventive_errors(self) -> dict[str, str]:
        blocking: dict[str, str] = {}
        if self._current_persona() is None:
            blocking["delegada"] = "⚠ Selecciona una delegada."

        fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
        try:
            datetime.strptime(fecha_pedida, "%Y-%m-%d")
        except ValueError:
            blocking["fecha"] = "⚠ Introduce una fecha válida."

        completo = self.completo_check.isChecked()
        tramo_errors = validate_request_inputs(
            None if completo else self.desde_input.time().toString("HH:mm"),
            None if completo else self.hasta_input.time().toString("HH:mm"),
            completo,
        )
        if tramo_errors:
            blocking["tramo"] = f"⚠ {next(iter(tramo_errors.values()))}"
        return blocking

    def _collect_preventive_business_rules(
        self,
        solicitud: SolicitudDTO,
        warnings: dict[str, str],
        blocking: dict[str, str],
    ) -> None:
        minutos = self._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        year, month, _ = (int(part) for part in solicitud.fecha_pedida.split("-"))
        saldos = self._solicitud_use_cases.calcular_saldos(solicitud.persona_id, year, month)
        if saldos.restantes_mes < minutos or saldos.restantes_ano < minutos:
            warnings["saldo"] = "Saldo insuficiente. La petición se ha registrado igualmente."

        duplicate = self._solicitud_use_cases.buscar_duplicado(solicitud)
        self._apply_duplicate_preventive_validation(solicitud, duplicate, blocking)

        similares = [
            item
            for item in self._solicitud_use_cases.buscar_similares(solicitud)
            if item.id != (duplicate.id if duplicate else None)
        ]
        if similares:
            ids_similares = [str(item.id) for item in similares if item.id is not None]
            warnings["similares"] = "Posibles similares: " + ", ".join(ids_similares)

        conflicto = self._solicitud_use_cases.validar_conflicto_dia(
            solicitud.persona_id, solicitud.fecha_pedida, solicitud.completo
        )
        if not conflicto.ok:
            blocking["conflicto"] = "⚠ Hay un conflicto activo pendiente en esa fecha."

        if solicitud.completo and self.cuadrante_warning_label.isVisible():
            warnings["cuadrante"] = "⚠ El cuadrante no está configurado y puede alterar el cálculo final."

    def _apply_duplicate_preventive_validation(
        self,
        solicitud: SolicitudDTO,
        duplicate: SolicitudDTO | None,
        blocking: dict[str, str],
    ) -> None:
        duplicate_message = "⚠ Ya existe una solicitud duplicada para la misma delegada, fecha y tramo."
        editing = self._selected_pending_for_editing()
        if duplicate is not None and (editing is None or duplicate.id != editing.id):
            blocking["duplicado"] = duplicate_message
            self._duplicate_target = duplicate

        pending_duplicate_row = self._find_pending_duplicate_row(solicitud)
        if pending_duplicate_row is not None:
            blocking["duplicado"] = duplicate_message
            self._duplicate_target = self._pending_solicitudes[pending_duplicate_row]

    def _collect_preventive_validation(self) -> tuple[dict[str, str], dict[str, str]]:
        blocking = self._collect_base_preventive_errors()
        warnings: dict[str, str] = {}
        self._duplicate_target = None

        solicitud = self._build_preview_solicitud()
        if solicitud is None or blocking:
            return blocking, warnings

        try:
            self._collect_preventive_business_rules(solicitud, warnings, blocking)
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                log_operational_error(
                    logger,
                    "DB locked during preventive validation",
                    exc=exc,
                    extra={
                        "operation": "preventive_validation",
                        "persona_id": solicitud.persona_id,
                    },
                )
                warnings["db"] = "⚠ Validación parcial temporal: base de datos ocupada."
            else:
                raise
        except (ValidacionError, BusinessRuleError) as exc:
            blocking.setdefault("tramo", f"⚠ {str(exc)}")

        self._dump_estado_pendientes("after_collect_preventive_validation")
        return blocking, warnings

    def _render_preventive_validation(self) -> None:
        if not self._ui_ready:
            return
        delegada_error = self._blocking_errors.get("delegada", "") if "delegada" in self._field_touched else ""
        fecha_error = self._blocking_errors.get("fecha", "") if "fecha" in self._field_touched else ""
        tramo_error = self._blocking_errors.get("tramo", "") if "tramo" in self._field_touched else ""

        self.delegada_field_error.setVisible(bool(delegada_error))
        self.delegada_field_error.setText(delegada_error)
        self.fecha_field_error.setVisible(bool(fecha_error))
        self.fecha_field_error.setText(fecha_error)
        self.tramo_field_error.setVisible(bool(tramo_error))
        self.tramo_field_error.setText(tramo_error)

        summary_items = [
            message for key, message in self._blocking_errors.items() if key not in {"delegada", "fecha", "tramo"} or key in self._field_touched
        ]
        if not summary_items:
            summary_items = list(self._blocking_errors.values())

        self.pending_errors_frame.setVisible(bool(summary_items))
        self.pending_errors_summary.setText("\n".join(f"• {message}" for message in summary_items))
        show_duplicate_cta = "duplicado" in self._blocking_errors and self._duplicate_target is not None
        self.goto_existing_button.setVisible(show_duplicate_cta)
        logger.debug(
            "duplicate_banner_updated visible=%s has_duplicate_error=%s duplicate_target_id=%s",
            show_duplicate_cta,
            "duplicado" in self._blocking_errors,
            self._duplicate_target.id if self._duplicate_target is not None else None,
        )

    def _on_go_to_existing_duplicate(self) -> None:
        duplicate = self._duplicate_target
        if duplicate is None:
            return
        if not duplicate.generated:
            if self._focus_pending_by_id(duplicate.id):
                return
            duplicate_row = self._find_pending_duplicate_row(duplicate)
            if duplicate_row is not None:
                self._focus_pending_row(duplicate_row)
                return
        self._focus_historico_duplicate(duplicate)

    def _run_preconfirm_checks(self) -> bool:
        self._field_touched.update({"delegada", "fecha", "tramo"})
        self._run_preventive_validation()
        if self._blocking_errors:
            self.toast.warning("Corrige los errores pendientes antes de confirmar.", title="Validación preventiva")
            return False
        if self._warnings:
            warning_text = "\n".join(f"• {msg}" for msg in self._warnings.values())
            self.toast.info(
                f"Se detectaron advertencias no bloqueantes:\n{warning_text}",
                title="Advertencias",
            )
        return True

    def _bind_manual_hours_preview_refresh(self) -> None:
        if not hasattr(self, "horas_input"):
            return
        horas_input = self.horas_input
        for signal_name in ("minutesChanged", "timeChanged", "valueChanged", "textChanged"):
            signal = getattr(horas_input, signal_name, None)
            if signal is None:
                continue
            try:
                signal.connect(self._update_solicitud_preview)
            except Exception:  # pragma: no cover - compatibilidad entre widgets Qt
                continue

    def _sync_completo_visibility(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        self.desde_container.setToolTip("No aplica en solicitud completa" if checked else "")
        self.hasta_container.setToolTip("No aplica en solicitud completa" if checked else "")

    def _on_edit_grupo(self) -> None:
        dialog = GrupoConfigDialog(self._grupo_use_cases, self._sync_service, self)
        if dialog.exec():
            self._refresh_saldos()

    def _on_sync(self) -> None:
        if not self._ui_ready:
            return
        if hasattr(self._sync_service, "is_configured") and not self._sync_service.is_configured():
            self.toast.warning(
                "Falta configurar Google Sheets o compartir la hoja con la cuenta de servicio.",
                title="Sync no disponible",
                action_label="Ver detalle",
                action_callback=lambda: self._show_error_detail(
                    titulo="Sync no disponible",
                    mensaje="Configura credenciales y comparte la hoja para habilitar la sincronización.",
                ),
            )
            return
        self._pending_sync_plan = None
        self._active_sync_id = None
        self._attempt_history = ()
        self._sync_attempts = []
        self.confirm_sync_button.setEnabled(False)
        self._sync_controller.on_sync()

    def _on_simulate_sync(self) -> None:
        self._sync_controller.on_simulate_sync()

    def _on_confirm_sync(self) -> None:
        if self._pending_sync_plan is not None and self._pending_sync_plan.conflicts:
            self.toast.warning("Conflictos pendientes de decisión", title="Sincronización bloqueada")
            return
        self._sync_controller.on_confirm_sync()

    def _on_retry_failed(self) -> None:
        if self._pending_sync_plan is None or self._last_sync_report is None:
            self.notifications.notify_operation(
                OperationFeedback(
                    title="Reintento no disponible",
                    happened="No hay un plan fallido que se pueda reintentar.",
                    affected_count=0,
                    incidents="No hay incidencias nuevas.",
                    next_step="Ejecuta una sincronización y revisa conflictos si aparecen.",
                    status="error",
                )
            )
            return
        item_status = {
            item.uuid: ("CONFLICT" if item in self._pending_sync_plan.conflicts else "ERROR")
            for item in [*self._pending_sync_plan.to_create, *self._pending_sync_plan.to_update, *self._pending_sync_plan.conflicts]
        }
        retry_result = self._retry_sync_use_case.build_retry_plan(self._pending_sync_plan, item_status=item_status)
        self._pending_sync_plan = retry_result.plan
        self.notifications.notify_operation(
            OperationFeedback(
                title="Reintento preparado",
                happened="Se reconstruyó el plan con los elementos en conflicto o error.",
                affected_count=len(item_status),
                incidents="Pendiente de ejecución.",
                next_step="Pulsa sincronizar para completar el reintento.",
            )
        )
        self._sync_controller.on_confirm_sync()

    def _on_show_sync_details(self) -> None:
        if self._last_sync_report is None:
            self.toast.info("Todavía no hay informes de sincronización.", title="Sincronización")
            return
        self._show_sync_details_dialog()

    def _on_copy_sync_report(self) -> None:
        if self._last_sync_report is None:
            return
        QApplication.clipboard().setText(to_markdown(self._last_sync_report))
        self.toast.success("Informe copiado al portapapeles.", title="Sincronización")

    def _on_open_sync_logs(self) -> None:
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        _abrir_archivo_local(self._logs_dir)

    def _on_sync_finished(self, summary: SyncSummary) -> None:
        self._pending_sync_plan = None
        self.confirm_sync_button.setEnabled(False)
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        self._refresh_last_sync_label()
        next_attempt_history = tuple(
            [
                *self._attempt_history,
                SyncAttemptReport(
                    attempt_number=len(self._attempt_history) + 1,
                    status=self._status_from_summary(summary),
                    created=summary.inserted_local + summary.inserted_remote,
                    updated=summary.updated_local + summary.updated_remote,
                    conflicts=summary.conflicts_detected,
                    errors=summary.errors,
                ),
            ]
        )
        report = build_sync_report(
            summary,
            status=self._status_from_summary(summary),
            source=self._sync_source_text(),
            scope=self._sync_scope_text(),
            actor=self._sync_actor_text(),
            started_at=self._sync_started_at,
            sync_id=self._active_sync_id,
            attempt_history=next_attempt_history,
        )
        self._active_sync_id = report.sync_id
        self._attempt_history = next_attempt_history
        self._apply_sync_report(report)
        self._refresh_after_sync(summary)
        status = self._status_from_summary(summary)
        feedback_status = "success"
        incidents = "Sin incidencias."
        if status == "OK_WARN":
            feedback_status = "partial"
            incidents = f"{summary.conflicts_detected} conflictos y {summary.errors} errores."
        elif status == "ERROR":
            feedback_status = "error"
            incidents = "La sincronización no se pudo completar."
        self.notifications.notify_operation(
            OperationFeedback(
                title=f"Resultado de sincronización: {self._status_to_label(status)}",
                happened="Se actualizó el estado del panel con el resumen persistente.",
                affected_count=summary.inserted_local + summary.inserted_remote + summary.updated_local + summary.updated_remote,
                incidents=incidents,
                next_step="Revisa conflictos o continúa operando según el estado mostrado.",
                status=feedback_status,
                action_label="Ver detalle",
                action_callback=self._on_show_sync_details,
            )
        )
        self._show_sync_summary_dialog(f"Resultado: {self._status_to_label(status)}", summary)

    def _on_sync_simulation_finished(self, plan: SyncExecutionPlan) -> None:
        self._set_sync_in_progress(False)
        self._pending_sync_plan = plan
        self._update_sync_button_state()
        report = build_simulation_report(
            plan,
            source=self._sync_source_text(),
            scope=self._sync_scope_text(),
            actor=self._sync_actor_text(),
            sync_id=self._active_sync_id,
            attempt_history=self._attempt_history,
        )
        self._apply_sync_report(report)
        has_changes = plan.has_changes
        self.confirm_sync_button.setEnabled(has_changes and not bool(plan.conflicts))
        self.retry_failed_button.setEnabled(bool(plan.conflicts or plan.potential_errors))
        if has_changes:
            self.toast.info(
                f"Se crearán: {len(plan.to_create)} · Se actualizarán: {len(plan.to_update)} · Sin cambios: {len(plan.unchanged)} · Conflictos detectados: {len(plan.conflicts)}",
                title="Simulación completada",
                duration_ms=7000,
            )
        else:
            self.toast.info("No hay cambios que aplicar", title="Simulación completada")

    def _refresh_after_sync(self, summary: SyncSummary) -> None:
        self._refresh_historico()
        self._refresh_saldos()
        self._refresh_pending_ui_state()
        if summary.inserted_local <= 0:
            return
        persona = self._current_persona()
        if persona is None or self.historico_proxy_model.rowCount() > 0:
            return
        if persona.id is None:
            return
        solicitudes_persona = self._solicitud_use_cases.listar_solicitudes_por_persona(persona.id)
        if any(True for _ in solicitudes_persona):
            self.toast.info(
                "Datos importados, pero no visibles por los filtros actuales de histórico.",
                title="Sincronización",
            )

    def _on_sync_failed(self, payload: object) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        error, details = self._normalize_sync_error(payload)
        if details:
            log_operational_error(
                logger,
                "Sync failed",
                exc=error,
                extra={
                    "operation": "sync_ui",
                    "correlation_id": getattr(self._sync_operation_context, "correlation_id", None),
                    "sync_id": self._active_sync_id,
                },
            )
        user_error = map_error_to_ui_message(error)
        user_message = user_error.as_text()
        report = build_failed_report(
            user_message,
            source=self._sync_source_text(),
            scope=self._sync_scope_text(),
            actor=self._sync_actor_text(),
            details=details,
            started_at=self._sync_started_at,
            sync_id=self._active_sync_id,
            attempt_history=self._attempt_history,
        )
        self._apply_sync_report(report)
        self.notifications.notify_operation(
            OperationFeedback(
                title="Sincronización con fallo",
                happened="No se pudo completar la sincronización.",
                affected_count=0,
                incidents="Se detectó un error durante el proceso.",
                next_step="Revisa el detalle y vuelve a intentar.",
                status="error",
                action_label="Ver detalle",
                action_callback=self._on_show_sync_details,
            )
        )
        self._show_sync_error_dialog(error, details)

    def _on_review_conflicts(self) -> None:
        dialog = ConflictsDialog(self._conflicts_service, self)
        dialog.exec()
        self._update_sync_button_state()
        self._update_conflicts_reminder()

    def _on_open_opciones(self) -> None:
        self._sync_controller.on_open_opciones()

    def _set_config_incomplete_state(self) -> None:
        report = build_config_incomplete_report(
            source=self._sync_source_text(),
            scope=self._sync_scope_text(),
            actor=self._sync_actor_text(),
        )
        self._apply_sync_report(report)
        self.go_to_sync_config_button.setVisible(True)

    def _on_edit_pdf(self) -> None:
        dialog = PdfConfigDialog(self._grupo_use_cases, self._sync_service, self)
        dialog.exec()

    def _manual_hours_minutes(self) -> int:
        if not hasattr(self, "horas_input"):
            return 0
        horas_input = self.horas_input
        if hasattr(horas_input, "minutes"):
            return max(0, int(horas_input.minutes()))
        if hasattr(horas_input, "time"):
            qtime = horas_input.time()
            return (qtime.hour() * 60) + qtime.minute()
        if hasattr(horas_input, "value"):
            return max(0, int(horas_input.value() * 60))
        return 0

    def _build_preview_solicitud(self) -> SolicitudDTO | None:
        persona = self._current_persona()
        if persona is None:
            return None
        completo = self.completo_check.isChecked()
        fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
        desde = None if completo else self.desde_input.time().toString("HH:mm")
        hasta = None if completo else self.hasta_input.time().toString("HH:mm")
        manual_minutes = self._manual_hours_minutes()
        editing_pending = self._selected_pending_for_editing()
        return SolicitudDTO(
            id=editing_pending.id if editing_pending is not None else None,
            persona_id=persona.id or 0,
            fecha_solicitud=datetime.now().strftime("%Y-%m-%d"),
            fecha_pedida=fecha_pedida,
            desde=desde,
            hasta=hasta,
            completo=completo,
            horas=manual_minutes / 60 if manual_minutes > 0 else 0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
            notas=None,
        )

    def _calculate_preview_minutes(self) -> tuple[int | None, bool]:
        solicitud = self._build_preview_solicitud()
        if solicitud is None:
            return 0, False
        try:
            minutos = self._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
            return minutos, False
        except BusinessRuleError as exc:
            mensaje = str(exc).lower()
            warning = solicitud.completo and "configura el cuadrante" in mensaje
            return None, warning

    def _update_solicitud_preview(self) -> None:
        if not self._ui_ready:
            return
        valid, message = self._validate_solicitud_form()
        minutos, warning = self._calculate_preview_minutes()
        total_txt = "—" if minutos is None or not valid else self._format_minutes(minutos)
        self.total_preview_input.setText(total_txt)
        if minutos is None or not valid:
            self.consequence_microcopy_label.setText("Esta acción consumirá 0 horas del saldo disponible.")
        else:
            self.consequence_microcopy_label.setText(
                f"Esta acción consumirá {self._format_minutes(minutos)} del saldo disponible."
            )
        self.cuadrante_warning_label.setVisible(warning)
        self.cuadrante_warning_label.setText("Cuadrante no configurado" if warning else "")
        self.solicitud_inline_error.setVisible(False)
        self.solicitud_inline_error.setText("")
        self._run_preventive_validation()
        self._update_action_state()

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        if self._current_persona() is None:
            return False, "Selecciona una persona para crear la solicitud."
        completo = self.completo_check.isChecked()
        errors = validate_request_inputs(
            None if completo else self.desde_input.time().toString("HH:mm"),
            None if completo else self.hasta_input.time().toString("HH:mm"),
            completo,
        )
        if errors:
            return False, next(iter(errors.values()))
        return True, ""

    def _update_action_state(self) -> None:
        if hasattr(self, "_run_preventive_validation"):
            self._run_preventive_validation()
        persona_selected = self._current_persona() is not None
        form_valid, form_message = self._validate_solicitud_form()
        blocking_errors = getattr(self, "_blocking_errors", {})
        has_blocking_errors = bool(blocking_errors)
        first_blocking_error = next(iter(blocking_errors.values()), "")
        editing_pending = self._selected_pending_for_editing()
        self.agregar_button.setEnabled(persona_selected and form_valid and not has_blocking_errors)
        self.agregar_button.setText("Actualizar pendiente" if editing_pending is not None else "Añadir a pendientes")
        has_pending = bool(self._pending_solicitudes)
        can_confirm = has_pending and not self._pending_conflict_rows and not has_blocking_errors
        self.insertar_sin_pdf_button.setEnabled(persona_selected and can_confirm)
        selected_pending = self._selected_pending_solicitudes()
        pendientes_count = len(self._iterar_pendientes_en_tabla())
        self.confirmar_button.setEnabled(debe_habilitar_confirmar_pdf(pendientes_count))
        self.edit_persona_button.setEnabled(persona_selected)
        self.delete_persona_button.setEnabled(persona_selected)
        self.edit_grupo_button.setEnabled(True)
        self.editar_pdf_button.setEnabled(True)
        selected_historico = self._selected_historico_solicitudes()
        self.eliminar_button.setEnabled(persona_selected and bool(selected_historico))
        self.eliminar_pendiente_button.setEnabled(bool(self._pending_solicitudes))
        self.ver_detalle_button.setEnabled(persona_selected and len(selected_historico) == 1)
        self.resync_historico_button.setEnabled(persona_selected and bool(selected_historico))
        self.generar_pdf_button.setEnabled(persona_selected and bool(selected_historico))
        selected_count = len(selected_historico)
        self.eliminar_button.setText(f"Eliminar ({selected_count})")
        self.ver_detalle_button.setText(f"Ver detalle ({selected_count})")
        self.resync_historico_button.setText(f"Re-sincronizar ({selected_count})")
        self.generar_pdf_button.setText(f"Generar PDF ({selected_count})")

        self._update_stepper_state(form_valid, has_blocking_errors, first_blocking_error, form_message)

        active_step = self._resolve_operativa_step(form_valid and not has_blocking_errors, has_pending, selected_pending, can_confirm)
        self._set_operativa_step(active_step)
        self._update_step_context(active_step)
        self._update_confirmation_summary(selected_pending)

        self._update_primary_cta(
            persona_selected=persona_selected,
            form_valid=form_valid,
            has_blocking_errors=has_blocking_errors,
            first_blocking_error=first_blocking_error,
            form_message=form_message,
            selected_pending=selected_pending,
            can_confirm=can_confirm,
            has_pending=has_pending,
        )
        self._dump_estado_pendientes("after_update_action_state")

    def _update_stepper_state(
        self,
        form_valid: bool,
        has_blocking_errors: bool,
        first_blocking_error: str,
        form_message: str,
    ) -> None:
        form_step_valid = form_valid and not has_blocking_errors
        self.stepper_labels[1].setEnabled(form_step_valid)
        stepper_message = first_blocking_error or form_message or "Completa la solicitud para poder añadirla"
        self.stepper_labels[1].setToolTip("" if form_step_valid else stepper_message)

    def _update_primary_cta(
        self,
        *,
        persona_selected: bool,
        form_valid: bool,
        has_blocking_errors: bool,
        first_blocking_error: str,
        form_message: str,
        selected_pending: list[SolicitudDTO],
        can_confirm: bool,
        has_pending: bool,
    ) -> None:
        can_confirm_selection = bool(selected_pending) and can_confirm
        editing_pending = self._selected_pending_for_editing()
        if can_confirm_selection:
            cta_text = "Confirmar seleccionadas"
        elif editing_pending is not None:
            cta_text = "Actualizar pendiente"
        else:
            cta_text = "Añadir a pendientes"
        self.primary_cta_button.setText(cta_text)

        if has_blocking_errors:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText(first_blocking_error)
            return

        if not form_valid:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText(form_message)
            return

        if can_confirm_selection or persona_selected:
            self.primary_cta_button.setEnabled(True)
            self.primary_cta_hint.setText("")
            return

        if has_pending:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText("Selecciona al menos una pendiente")
            return

        self.primary_cta_button.setEnabled(False)
        self.primary_cta_hint.setText("Completa el formulario para continuar")

    def _resolve_operativa_step(
        self,
        form_valid: bool,
        has_pending: bool,
        selected_pending: list[SolicitudDTO],
        can_confirm: bool,
    ) -> int:
        if selected_pending and can_confirm:
            return 3
        if has_pending:
            return 2
        if form_valid:
            return 2
        return 1

    def _set_operativa_step(self, active_step: int) -> None:
        for index, label in enumerate(self.stepper_labels, start=1):
            if index < active_step:
                label.setProperty("role", "stepDone")
            elif index == active_step:
                label.setProperty("role", "stepActive")
            else:
                label.setProperty("role", "stepIdle")
            label.style().unpolish(label)
            label.style().polish(label)

        for index, bullet in enumerate(self._step_bullets, start=1):
            if index < active_step:
                bullet.setText("✓")
                bullet.setProperty("role", "stepBulletDone")
            elif index == active_step:
                bullet.setText(str(index))
                bullet.setProperty("role", "stepBulletActive")
            else:
                bullet.setText(str(index))
                bullet.setProperty("role", "stepBulletIdle")
            bullet.style().unpolish(bullet)
            bullet.style().polish(bullet)

    def _update_step_context(self, active_step: int) -> None:
        messages = {
            1: "Pendientes: 0 · Seleccionadas: 0 · Modo: Delegada",
            2: "Pendientes en revisión",
            3: "Lista para confirmar y generar PDF",
        }
        self.stepper_context_label.setText(messages.get(active_step, ""))

    def _update_confirmation_summary(self, selected_pending: list[SolicitudDTO]) -> None:
        if not selected_pending:
            self.confirmation_summary_label.clear()
            self.confirmation_summary_label.setVisible(False)
            return

        persona = self._current_persona()
        delegada = persona.nombre if persona is not None else "Sin delegada"
        modo = "Todas" if self._pending_view_all else f"Delegada: {delegada}"
        total_min = self._sum_solicitudes_minutes(selected_pending)
        self.confirmation_summary_label.setText(
            f"Pendientes: {len(self._pending_solicitudes)} · Seleccionadas: {len(selected_pending)} · Modo: {modo} · Total: {self._format_minutes(total_min)}"
        )
        self.confirmation_summary_label.setVisible(True)

    def _selected_pending_solicitudes(self) -> list[SolicitudDTO]:
        selected_rows = self._selected_pending_row_indexes()
        return [self._pending_solicitudes[row] for row in selected_rows if 0 <= row < len(self._pending_solicitudes)]

    def _on_primary_cta_clicked(self) -> None:
        self._dump_estado_pendientes("click_primary_cta")
        if self.primary_cta_button.text() == "Confirmar seleccionadas":
            self._on_confirmar()
            return
        self._on_add_pendiente()

    def _build_debug_estado_pendientes(self) -> dict[str, object]:
        editing_pending = self._selected_pending_for_editing()
        selected_rows = self._selected_pending_row_indexes()
        solicitud = self._build_preview_solicitud()
        dto_form_actual = None
        clave_form_normalizada = None
        duplicate_eval: dict[str, object] = {
            "function": "hay_duplicado_distinto",
            "params": {
                "solicitud": None,
                "existentes_count": len(self._pending_solicitudes),
                "excluir_por_id": editing_pending.id if editing_pending is not None else None,
                "excluir_por_indice": selected_rows[0] if editing_pending is not None and selected_rows else None,
            },
            "resultado": None,
        }
        if solicitud is not None:
            dto_form_actual = {
                "persona_id": solicitud.persona_id,
                "fecha": solicitud.fecha_pedida,
                "desde": solicitud.desde,
                "hasta": solicitud.hasta,
                "completo": solicitud.completo,
            }
            clave_form_normalizada = list(clave_duplicado_solicitud(solicitud))
            duplicate_eval["params"]["solicitud"] = dto_form_actual
            duplicate_eval["resultado"] = hay_duplicado_distinto(
                solicitud,
                self._pending_solicitudes,
                excluir_por_id=duplicate_eval["params"]["excluir_por_id"],
                excluir_por_indice=duplicate_eval["params"]["excluir_por_indice"],
            )

        lista_pendientes = []
        for index, pendiente in enumerate(self._pending_solicitudes):
            lista_pendientes.append(
                {
                    "id": pendiente.id,
                    "index": index,
                    "clave_normalizada": list(clave_duplicado_solicitud(pendiente)),
                }
            )

        cta_text = self.primary_cta_button.text() if self.primary_cta_button is not None else ""
        if cta_text == "Actualizar pendiente":
            cta_reason = "editing_pending_selected"
        elif cta_text == "Añadir a pendientes":
            cta_reason = "default_add_mode"
        elif cta_text == "Confirmar seleccionadas":
            cta_reason = "selected_pending_can_confirm"
        else:
            cta_reason = "cta_hidden_or_unknown"

        return {
            "editing_pending_id": editing_pending.id if editing_pending is not None else None,
            "editing_pending_index": selected_rows[0] if editing_pending is not None and selected_rows else None,
            "selected_pending_rows": selected_rows,
            "selected_pending_count": len(selected_rows),
            "dto_form_actual": dto_form_actual,
            "clave_form_normalizada": clave_form_normalizada,
            "lista_pendientes": lista_pendientes,
            "hay_duplicado_distinto": duplicate_eval,
            "cta_decision": {
                "text": cta_text,
                "enabled": bool(self.primary_cta_button.isEnabled()) if self.primary_cta_button is not None else False,
                "reason": cta_reason,
                "hint": self.primary_cta_hint.text() if self.primary_cta_hint is not None else "",
            },
        }

    def _dump_estado_pendientes(self, motivo: str) -> dict:
        try:
            estado = self._build_debug_estado_pendientes()
        except Exception as exc:  # pragma: no cover - diagnóstico defensivo
            estado = {"motivo": motivo, "error": str(exc)}
            logger.exception("estado_pendientes_failed motivo=%s", motivo)
            return estado
        logger.debug("estado_pendientes[%s]=%s", motivo, json.dumps(estado, ensure_ascii=False, default=str, indent=2))
        return estado

    def _on_pending_selection_changed(self) -> None:
        # Para juniors: mantener este hook separado facilita leer por qué cambia el CTA.
        self._dump_estado_pendientes("selection_changed_pending")
        self._update_action_state()

    def _undo_last_added_pending(self, solicitud_id: int | None) -> None:
        if solicitud_id is None:
            return
        try:
            with OperationContext("deshacer_pendiente") as operation:
                self._solicitud_use_cases.eliminar_solicitud(
                    solicitud_id,
                    correlation_id=operation.correlation_id,
                )
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error al deshacer pendiente")
            self._show_critical_error(exc)
            return
        self._reload_pending_views()
        self._refresh_saldos()
        self.toast.info("Pendiente deshecha")

    def _refresh_pending_conflicts(self) -> None:
        conflict_rows: set[int] = set()
        if self._pending_solicitudes:
            try:
                conflict_rows = self._solicitud_use_cases.detectar_conflictos_pendientes(
                    self._pending_solicitudes
                )
            except BusinessRuleError as exc:
                logger.warning("No se pudieron calcular conflictos de pendientes: %s", exc)

        previously_conflicting = bool(self._pending_conflict_rows)
        self._pending_conflict_rows = conflict_rows
        self.pendientes_model.set_conflict_rows(conflict_rows)

        if conflict_rows and not previously_conflicting:
            self.toast.warning(
                "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                title="Conflictos detectados",
            )

    def _refresh_pending_ui_state(self) -> None:
        self.pendientes_model.set_show_delegada(self._pending_view_all)
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._configure_solicitudes_table(self.pendientes_table)
        self._update_pending_totals()
        self._refresh_pending_conflicts()
        self._update_action_state()
        self._update_global_context()

    def _reconstruir_tabla_pendientes(self) -> None:
        self._refresh_pending_ui_state()
        if self._pending_solicitudes:
            return
        self._duplicate_target = None
        self._blocking_errors.pop("duplicado", None)
        self.goto_existing_button.setVisible(False)
        self._render_preventive_validation()

    def _refrescar_historico(self) -> None:
        self._refresh_historico()

    def _procesar_resultado_confirmacion(self, confirmadas_ids: list[int], errores: list[str]) -> None:
        self._pending_all_solicitudes = aplicar_confirmacion(self._pending_all_solicitudes, confirmadas_ids)
        self._pending_solicitudes = aplicar_confirmacion(self._pending_solicitudes, confirmadas_ids)
        self._hidden_pendientes = aplicar_confirmacion(self._hidden_pendientes, confirmadas_ids)
        self._orphan_pendientes = aplicar_confirmacion(self._orphan_pendientes, confirmadas_ids)
        self._reconstruir_tabla_pendientes()
        self._refrescar_historico()
        self._refresh_saldos()
        self.toast.success(f"{len(confirmadas_ids)} solicitudes confirmadas", title="Confirmación")
        if errores:
            self.toast.warning(f"{len(errores)} errores", title="Confirmación")
        logger.info(
            "UI_CONFIRMAR_RESULT",
            extra={
                "confirmadas": len(confirmadas_ids),
                "errores": len(errores),
                "pendientes_restantes": len(self._pending_solicitudes),
            },
        )

    def _selected_historico(self) -> SolicitudDTO | None:
        selected = self._selected_historico_solicitudes()
        return selected[0] if selected else None

    def _selected_historico_solicitudes(self) -> list[SolicitudDTO]:
        selection = self.historico_table.selectionModel().selectedRows()
        if not selection:
            return []
        solicitudes: list[SolicitudDTO] = []
        for proxy_index in selection:
            source_index = self.historico_proxy_model.mapToSource(proxy_index)
            solicitud = self.historico_model.solicitud_at(source_index.row())
            if solicitud is not None:
                solicitudes.append(solicitud)
        return solicitudes

    def _on_add_persona(self) -> None:
        dialog = PersonaDialog(self)
        persona_dto = dialog.get_persona()
        if persona_dto is None:
            logger.info("Creación de persona cancelada")
            return
        self._personas_controller.on_add_persona(persona_dto)

    def _on_edit_persona(self) -> None:
        persona = self._selected_config_persona()
        if persona is None:
            self.toast.warning("Selecciona una delegada válida para editar.", title="Delegada requerida")
            return
        dialog = PersonaDialog(self, persona)
        persona_dto = dialog.get_persona()
        if persona_dto is None:
            logger.info("Edición de persona cancelada")
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar cambios",
            "¿Confirmas los cambios? Esto afectará a cálculos futuros.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            actualizada = self._persona_use_cases.editar_persona(persona_dto)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error editando persona")
            self._show_critical_error(exc)
            return
        self._load_personas(select_id=actualizada.id)

    def _on_delete_persona(self) -> None:
        persona = self._selected_config_persona()
        if persona is None:
            self.toast.warning("Selecciona una delegada válida para eliminar.", title="Delegada requerida")
            return
        logger.info("Se pide confirmación de borrado motivo=policy=always_confirm selection_count=1")
        respuesta = QMessageBox.question(
            self,
            "Eliminar delegado",
            f"¿Deseas deshabilitar a {persona.nombre}? El histórico se conservará.",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        try:
            self._persona_use_cases.desactivar_persona(persona.id or 0)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error deshabilitando delegado")
            self._show_critical_error(exc)
            return
        self._load_personas()

    def _on_add_pendiente(self) -> None:
        logger.info("CLICK add_or_update_pendiente handler=_on_add_pendiente")
        self._dump_estado_pendientes("click_add_or_update_pending")
        if not self._ui_ready:
            logger.info("_on_add_pendiente early_return motivo=ui_not_ready")
            return
        self._field_touched.update({"delegada", "fecha", "tramo"})
        self._run_preventive_validation()
        if self._blocking_errors:
            logger.info("_on_add_pendiente early_return motivo=blocking_errors")
            self.toast.warning("Corrige los errores pendientes antes de añadir.", title="Validación preventiva")
            return
        self._solicitudes_controller.on_add_pendiente()

    def _selected_pending_row_indexes(self) -> list[int]:
        selection_model = self.pendientes_table.selectionModel()
        if selection_model is None:
            return []
        return sorted({index.row() for index in selection_model.selectedRows()})

    def _selected_pending_for_editing(self) -> SolicitudDTO | None:
        rows = self._selected_pending_row_indexes()
        if len(rows) != 1:
            return None
        row = rows[0]
        if row < 0 or row >= len(self._pending_solicitudes):
            return None
        return self._pending_solicitudes[row]

    def _find_pending_duplicate_row(self, solicitud: SolicitudDTO) -> int | None:
        editing = self._selected_pending_for_editing()
        editing_row = self._selected_pending_row_indexes()[0] if editing is not None else None
        excluir_por_id = editing.id if editing is not None else None
        excluir_por_indice = editing_row

        try:
            clave_objetivo = clave_duplicado_solicitud(solicitud)
        except Exception:
            return None

        logger.info(
            "UI_PREVENTIVE_DUPLICATE_CHECK clave=%s excluir_id=%s excluir_idx=%s",
            list(clave_objetivo),
            excluir_por_id,
            excluir_por_indice,
        )

        coincidencias: list[int] = []
        for row, pending in enumerate(self._pending_solicitudes):
            if excluir_por_id is not None and pending.id is not None and str(pending.id) == str(excluir_por_id):
                continue
            if pending.id is None and excluir_por_indice is not None and row == excluir_por_indice:
                continue
            try:
                if clave_duplicado_solicitud(pending) == clave_objetivo:
                    coincidencias.append(row)
            except Exception:
                continue

        is_duplicate = bool(coincidencias)
        logger.info(
            "UI_PREVENTIVE_DUPLICATE_RESULT is_duplicate=%s coincidencias=%s",
            is_duplicate,
            coincidencias,
        )

        hay_duplicado = hay_duplicado_distinto(
            solicitud,
            self._pending_solicitudes,
            excluir_por_id=excluir_por_id,
            excluir_por_indice=excluir_por_indice,
        )
        if not hay_duplicado:
            return None
        return coincidencias[0] if coincidencias else (0 if self._pending_solicitudes else None)

    def _find_pending_row_by_id(self, solicitud_id: int | None) -> int | None:
        if solicitud_id is None:
            return None
        for row, pending in enumerate(self._pending_solicitudes):
            if pending.id == solicitud_id:
                return row
        return None

    def _handle_duplicate_before_add(self, duplicate_row: int) -> bool:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Pendiente duplicada")
        dialog.setText("Ya existe una pendiente igual para esta delegada, fecha y tramo horario.")
        dialog.setInformativeText("Puedes ir a la existente o crear igualmente.")
        goto_button = dialog.addButton("Ir a la pendiente existente", QMessageBox.AcceptRole)
        create_button = dialog.addButton("Crear igualmente", QMessageBox.ActionRole)
        cancel_button = dialog.addButton("Cancelar", QMessageBox.RejectRole)
        create_button.setEnabled(False)
        create_button.setToolTip("No permitido por la regla de negocio de duplicados.")
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is goto_button:
            self._focus_pending_row(duplicate_row)
            return False
        if clicked is create_button:
            return True
        if clicked is cancel_button:
            return False
        return False

    def _focus_pending_row(self, row: int) -> None:
        if row < 0 or row >= self.pendientes_model.rowCount():
            return
        self.pendientes_table.selectRow(row)
        model_index = self.pendientes_model.index(row, 0)
        self.pendientes_table.scrollTo(model_index, QAbstractItemView.PositionAtCenter)
        self.pendientes_table.setFocus()

    def _focus_pending_by_id(self, solicitud_id: int | None) -> bool:
        row = self._find_pending_row_by_id(solicitud_id)
        if row is None:
            return False
        self._focus_pending_row(row)
        return True

    def _focus_historico_duplicate(self, solicitud: SolicitudDTO) -> None:
        self._refresh_historico()
        for row in range(self.historico_model.rowCount()):
            model_solicitud = self.historico_model.solicitud_at(row)
            if model_solicitud is None:
                continue
            if model_solicitud.id == solicitud.id:
                source_index = self.historico_model.index(row, 0)
                proxy_index = self.historico_proxy_model.mapFromSource(source_index)
                if not proxy_index.isValid():
                    continue
                self.historico_table.selectRow(proxy_index.row())
                self.historico_table.scrollTo(
                    proxy_index, QAbstractItemView.PositionAtCenter
                )
                self.main_tabs.setCurrentIndex(1)
                return

    def _handle_duplicate_detected(self, duplicate: SolicitudDTO) -> bool:
        is_pending = not duplicate.generated
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Solicitud duplicada")
        if is_pending:
            dialog.setText("Ya existe una solicitud pendiente igual.")
            dialog.setInformativeText("Puedes ir a la pendiente existente para gestionarla.")
            goto_button = dialog.addButton("Ir a la pendiente existente", QMessageBox.AcceptRole)
        else:
            dialog.setText("La solicitud ya está confirmada en histórico.")
            dialog.setInformativeText("Puedes abrir el histórico para revisarla.")
            goto_button = dialog.addButton("Ir al histórico", QMessageBox.AcceptRole)
        dialog.addButton("Cancelar", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() is not goto_button:
            return False

        if is_pending:
            if self._focus_pending_by_id(duplicate.id):
                return False
            if not self._pending_view_all:
                self.ver_todas_pendientes_button.setChecked(True)
            self._reload_pending_views()
            self._focus_pending_by_id(duplicate.id)
            return False

        self._focus_historico_duplicate(duplicate)
        return False

    def _resolve_pending_conflict(self, fecha_pedida: str, completo: bool) -> bool:
        conflictos = [
            index
            for index, solicitud in enumerate(self._pending_solicitudes)
            if solicitud.fecha_pedida == fecha_pedida and solicitud.completo != completo
        ]
        if not conflictos:
            return True
        mensaje = (
            "Hay horas parciales. ¿Sustituirlas por COMPLETO?"
            if completo
            else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
        )
        if not self._confirm_conflicto(mensaje):
            return False
        for index in sorted(conflictos, reverse=True):
            self._pending_solicitudes.pop(index)
        self._refresh_pending_ui_state()
        return True

    def _resolve_backend_conflict(self, persona_id: int, solicitud: SolicitudDTO) -> bool:
        try:
            conflicto = self._solicitud_use_cases.validar_conflicto_dia(
                persona_id, solicitud.fecha_pedida, solicitud.completo
            )
        except BusinessRuleError as exc:
            self.toast.warning(str(exc), title="Validación")
            return False
        if conflicto.ok:
            return True
        mensaje = (
            "Hay horas parciales. ¿Sustituirlas por COMPLETO?"
            if solicitud.completo
            else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
        )
        if not self._confirm_conflicto(mensaje):
            return False
        try:
            with OperationContext("sustituir_solicitud") as operation:
                if solicitud.completo:
                    self._solicitud_use_cases.sustituir_por_completo(
                        persona_id,
                        solicitud.fecha_pedida,
                        solicitud,
                        correlation_id=operation.correlation_id,
                    )
                else:
                    self._solicitud_use_cases.sustituir_por_parcial(
                        persona_id,
                        solicitud.fecha_pedida,
                        solicitud,
                        correlation_id=operation.correlation_id,
                    )
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return False
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error sustituyendo solicitud")
            self._show_critical_error(exc)
            return False
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self.notas_input.setPlainText("")
        return True

    def _on_insertar_sin_pdf(self) -> None:
        logger.info("CLICK confirmar_sin_pdf handler=_on_insertar_sin_pdf")
        self._dump_estado_pendientes("click_confirmar_sin_pdf")
        if not self._run_preconfirm_checks():
            logger.info("_on_insertar_sin_pdf early_return motivo=preconfirm_checks")
            return
        persona = self._current_persona()
        selected = self._selected_pending_solicitudes()
        if persona is None:
            logger.info("_on_insertar_sin_pdf early_return motivo=no_persona")
            return
        warning_message = validar_seleccion_confirmacion(len(selected))
        if warning_message:
            self.toast.warning(warning_message, title="Selección requerida")
            logger.info("_on_insertar_sin_pdf early_return motivo=sin_seleccion")
            return
        if self._pending_conflict_rows:
            logger.info("_on_insertar_sin_pdf early_return motivo=conflictos_pendientes")
            self.toast.warning(
                "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                title="Conflictos detectados",
            )
            return

        try:
            self._set_processing_state(True)
            with OperationContext("confirmar_sin_pdf") as operation:
                log_event(logger, "confirmar_sin_pdf_started", {"count": len(selected)}, operation.correlation_id)
                confirmadas_ids, errores, _ruta, creadas = self._solicitudes_controller.confirmar_lote(
                    selected,
                    correlation_id=operation.correlation_id,
                    generar_pdf=False,
                )
                self._procesar_resultado_confirmacion(confirmadas_ids, errores)
                log_event(
                    logger,
                    "confirmar_sin_pdf_finished",
                    {"creadas": len(creadas), "errores": len(errores)},
                    operation.correlation_id,
                )
                self._show_confirmation_closure(
                    creadas,
                    errores,
                    operation_name="confirmar_sin_pdf",
                    correlation_id=operation.correlation_id,
                )
                self._notify_historico_filter_if_hidden(creadas)
        finally:
            self._set_processing_state(False)

    def _on_confirmar(self) -> None:
        try:
            logger.info("CLICK confirmar_pdf handler=_on_confirmar")
            self._dump_estado_pendientes("click_confirmar_pdf")
            pendientes_en_tabla = self._iterar_pendientes_en_tabla()
            print("DEBUG_PENDIENTES_COUNT", len(pendientes_en_tabla))
            for pendiente in pendientes_en_tabla:
                print("DEBUG_PENDIENTE", pendiente)

            selected = [
                self.pendientes_model.solicitud_at(item["row"])
                for item in pendientes_en_tabla
                if self.pendientes_model is not None
            ]
            selected = [sol for sol in selected if sol is not None]
            selected_ids = [sol.id for sol in selected]
            editing = self._selected_pending_for_editing()
            persona = self._current_persona()
            log_extra = {
                "selected_count": len(selected),
                "selected_ids": selected_ids,
                "editing_id": editing.id if editing is not None else None,
                "persona_id": persona.id if persona is not None else None,
                "fecha": self.fecha_input.date().toString("yyyy-MM-dd"),
                "desde": self.desde_input.time().toString("HH:mm"),
                "hasta": self.hasta_input.time().toString("HH:mm"),
            }
            logger.info("UI_CLICK_CONFIRMAR_PDF", extra=log_extra)

            def _return_early(reason: str) -> None:
                logger.warning("UI_CONFIRMAR_PDF_RETURN_EARLY", extra={**log_extra, "reason": reason})

            if not self._ui_ready:
                logger.info("_on_confirmar early_return motivo=ui_not_ready")
                _return_early("ui_not_ready")
                return
            logger.debug("_on_confirmar paso=validar_preconfirm_checks")
            if not selected:
                self.toast.warning("No hay pendientes", title="Sin pendientes")
                logger.info("_on_confirmar early_return motivo=no_pending_rows")
                _return_early("no_pending_rows")
                return
            if not self._run_preconfirm_checks():
                logger.info("_on_confirmar early_return motivo=preconfirm_checks")
                _return_early("preconfirm_checks")
                return
            logger.debug("_on_confirmar paso=seleccion_pendientes rows=%s ids=%s", self._selected_pending_row_indexes(), selected_ids)
            if persona is None:
                logger.info("_on_confirmar early_return motivo=no_persona")
                _return_early("no_persona")
                return
            if self._pending_conflict_rows:
                logger.info("_on_confirmar early_return motivo=conflictos_pendientes")
                self.toast.warning(
                    "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                    title="Conflictos detectados",
                )
                _return_early("conflictos_pendientes")
                return

            pdf_path = self._prompt_confirm_pdf_path(selected)
            if pdf_path is None:
                logger.info("_on_confirmar early_return motivo=pdf_path_cancelado")
                _return_early("pdf_path_cancelado")
                return
            logger.debug("_on_confirmar paso=pdf_path_seleccionado path=%s", pdf_path)

            logger.debug("_on_confirmar paso=llamar_execute_confirmar_with_pdf")
            outcome = self._execute_confirmar_with_pdf(persona, selected, pdf_path)
            if outcome is None:
                logger.info("_on_confirmar early_return motivo=execute_confirmar_none")
                _return_early("execute_confirmar_none")
                return
            correlation_id, generado, creadas, confirmadas_ids, errores = outcome
            logger.debug("_on_confirmar paso=resultado_execute pdf_generado=%s", str(generado) if generado else None)

            self._finalize_confirmar_with_pdf(persona, correlation_id, generado, creadas, confirmadas_ids, errores)
        except Exception:
            logger.exception("UI_CONFIRMAR_PDF_EXCEPTION")
            raise

    def _iterar_pendientes_en_tabla(self) -> list[dict[str, object]]:
        if self.pendientes_table is None:
            return []
        model = self.pendientes_table.model()
        if model is None:
            return []

        total_rows = model.rowCount()
        total_cols = model.columnCount()
        delegada_col: int | None = None
        for col in range(total_cols):
            header = model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
            if str(header).strip().lower() == "delegada":
                delegada_col = col
                break

        pendientes: list[dict[str, object]] = []
        for row in range(total_rows):
            solicitud = self.pendientes_model.solicitud_at(row) if self.pendientes_model is not None else None
            fecha = model.index(row, 0).data() if total_cols > 0 else ""
            desde = model.index(row, 1).data() if total_cols > 1 else ""
            hasta = model.index(row, 2).data() if total_cols > 2 else ""
            delegada = model.index(row, delegada_col).data() if delegada_col is not None else None
            pendientes.append(
                {
                    "row": row,
                    "id": solicitud.id if solicitud is not None else None,
                    "fecha": fecha if fecha not in (None, "-") else "",
                    "desde": desde if desde not in (None, "-") else "",
                    "hasta": hasta if hasta not in (None, "-") else "",
                    "persona_id": solicitud.persona_id if solicitud is not None else None,
                    "delegada": delegada if delegada not in (None, "-") else None,
                }
            )
        return pendientes

    def _prompt_confirm_pdf_path(self, selected: list[SolicitudDTO]) -> str | None:
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(selected)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return None
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF")
            self._show_critical_error(exc)
            return None

        default_path = str(Path.home() / default_name)
        pdf_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_path, "PDF (*.pdf)")
        return pdf_path or None

    def _execute_confirmar_with_pdf(
        self,
        persona: PersonaDTO,
        selected: list[SolicitudDTO],
        pdf_path: str,
    ) -> tuple[str | None, Path | None, list[SolicitudDTO], list[int], list[str]] | None:
        correlation_id: str | None = None
        try:
            self._set_processing_state(True)
            with OperationContext("confirmar_y_generar_pdf") as operation:
                correlation_id = operation.correlation_id
                logger.debug("_execute_confirmar_with_pdf paso=validar_seleccion count=%s", len(selected))
                logger.debug("_execute_confirmar_with_pdf paso=ids_seleccionadas ids=%s", [sol.id for sol in selected])
                log_event(
                    logger,
                    "confirmar_y_generar_pdf_started",
                    {"count": len(selected), "destino": pdf_path},
                    operation.correlation_id,
                )
                confirmadas_ids, errores, generado, creadas = self._solicitudes_controller.confirmar_lote(
                    selected,
                    correlation_id=operation.correlation_id,
                    generar_pdf=True,
                    pdf_path=pdf_path,
                    filtro_delegada=None if self._pending_view_all else (persona.id or None),
                )
                logger.debug("_execute_confirmar_with_pdf paso=llamada_servicio_confirmar ok=True")
                logger.debug("_execute_confirmar_with_pdf paso=llamada_generador_pdf ruta=%s", str(generado) if generado else "")
                log_event(
                    logger,
                    "confirmar_y_generar_pdf_finished",
                    {"creadas": len(creadas), "errores": len(errores), "pdf_generado": bool(generado)},
                    operation.correlation_id,
                )
                return correlation_id, generado, creadas, confirmadas_ids, errores
        except Exception as exc:  # pragma: no cover - fallback
            if isinstance(exc, OSError):
                log_operational_error(
                    logger,
                    "File export failed during confirm+PDF",
                    exc=exc,
                    extra={
                        "operation": "confirmar_y_generar_pdf",
                        "persona_id": persona.id or 0,
                        "correlation_id": correlation_id,
                    },
                )
            else:
                logger.exception("Error confirmando solicitudes")
            self._show_critical_error(exc)
            return None
        finally:
            self._set_processing_state(False)

    def _finalize_confirmar_with_pdf(
        self,
        persona: PersonaDTO,
        correlation_id: str | None,
        generado: Path | None,
        creadas: list[SolicitudDTO],
        confirmadas_ids: list[int],
        errores: list[str],
    ) -> None:
        logger.debug("_finalize_confirmar_with_pdf paso=ruta_pdf_final ruta=%s", str(generado) if generado else None)
        if generado and self.abrir_pdf_check.isChecked():
            logger.debug("_finalize_confirmar_with_pdf paso=intento_abrir_pdf enabled=True")
            _abrir_archivo_local(generado)
        if generado and creadas:
            pdf_hash = creadas[0].pdf_hash
            fechas = [solicitud.fecha_pedida for solicitud in creadas]
            self._sync_service.register_pdf_log(persona.id or 0, fechas, pdf_hash)
            if correlation_id:
                log_event(
                    logger,
                    "register_pdf_log",
                    {"persona_id": persona.id or 0, "fechas": len(fechas)},
                    correlation_id,
                )
            self._ask_push_after_pdf()
            self._toast_success(
                "PDF generado correctamente",
                title="Confirmación",
                action_label="Abrir PDF",
                action_callback=lambda: _abrir_archivo_local(generado),
            )
            _abrir_archivo_local(generado)
        self._procesar_resultado_confirmacion(confirmadas_ids, errores)
        self._show_confirmation_closure(
            creadas,
            errores,
            operation_name="confirmar_y_generar_pdf",
            correlation_id=correlation_id,
        )
        self._notify_historico_filter_if_hidden(creadas)

    def _toast_success(self, msg: str, title: str, **kwargs: object) -> None:
        try:
            self.toast.success(msg, title=title, **kwargs)
        except TypeError:
            logger.warning("UI_TOAST_DEGRADED: success toast fallback without kwargs", extra={"kwargs": list(kwargs.keys())})
            self.toast.success(msg, title=title)

    def _sum_solicitudes_minutes(self, solicitudes: list[SolicitudDTO]) -> int:
        return sum(int(round(solicitud.horas * 60)) for solicitud in solicitudes)

    def _show_confirmation_closure(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
        *,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> None:
        payload = self._build_confirmation_payload(creadas, errores, correlation_id=correlation_id)
        log_event(
            logger,
            "confirmation_closure_recorded",
            {
                "operation": operation_name,
                "result_id": payload.result_id,
                "status": payload.status,
                "count": payload.count,
                "delegadas": payload.delegadas,
                "total_minutes": payload.total_minutes,
                "saldo_disponible": payload.saldo_disponible,
                "errores": payload.errores,
                "timestamp": payload.timestamp,
            },
            payload.correlation_id or correlation_id or payload.result_id,
        )
        self.notifications.show_confirmation_closure(payload)

    def _build_confirmation_payload(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
        *,
        correlation_id: str | None = None,
    ) -> ConfirmationSummaryPayload:
        persona_nombres = {persona.id: persona.nombre for persona in self._personas if persona.id is not None}
        delegadas = sorted({persona_nombres.get(s.persona_id, f"ID {s.persona_id}") for s in creadas})
        if not creadas:
            status = "error"
        elif errores:
            status = "partial"
        else:
            status = "success"
        undo_ids = [solicitud.id for solicitud in creadas if solicitud.id is not None]
        return ConfirmationSummaryPayload(
            count=len(creadas),
            total_minutes=self._sum_solicitudes_minutes(creadas),
            delegadas=delegadas,
            saldo_disponible=self.saldos_card.saldo_periodo_restante_text(),
            errores=errores,
            status=status,
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            result_id=f"CFM-{datetime.now().strftime('%y%m%d%H%M%S')}",
            correlation_id=correlation_id,
            on_view_history=self._focus_historico_search,
            on_sync_now=self._on_push_now,
            on_return_to_operativa=lambda: self.main_tabs.setCurrentIndex(0),
            undo_seconds=12 if undo_ids else None,
            on_undo=(lambda: self._undo_confirmation(undo_ids)) if undo_ids else None,
        )

    def _undo_confirmation(self, solicitud_ids: list[int]) -> None:
        if self._sync_in_progress:
            self.toast.warning("La sincronización está en curso. Ahora no se puede deshacer.", title="Deshacer no disponible")
            return
        removed = 0
        for solicitud_id in solicitud_ids:
            try:
                with OperationContext("deshacer_confirmacion") as operation:
                    self._solicitud_use_cases.eliminar_solicitud(solicitud_id, correlation_id=operation.correlation_id)
                removed += 1
            except BusinessRuleError:
                continue
        self._reload_pending_views()
        self._refresh_historico()
        self._refresh_saldos()
        if removed:
            self.toast.success(f"Se deshicieron {removed} confirmaciones.")

    def _ask_push_after_pdf(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("PDF generado")
        dialog.setText("PDF generado. ¿Quieres sincronizar ahora con Google Sheets?")
        subir_button = dialog.addButton("Subir ahora", QMessageBox.AcceptRole)
        dialog.addButton("Más tarde", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() != subir_button:
            return
        self._on_push_now()

    def _on_push_now(self) -> None:
        if not self._sync_service.is_configured():
            self.toast.warning("No hay configuración de Google Sheets. Abre Opciones para configurarlo.", title="Sin configuración")
            return
        self._set_sync_in_progress(True)
        self._sync_thread = QThread()
        self._sync_worker = PushWorker(self._sync_service)
        self._sync_worker.moveToThread(self._sync_thread)
        self._sync_thread.started.connect(self._sync_worker.run)
        self._sync_worker.finished.connect(self._on_push_finished)
        self._sync_worker.failed.connect(self._on_push_failed)
        self._sync_worker.finished.connect(self._sync_thread.quit)
        self._sync_worker.finished.connect(self._sync_worker.deleteLater)
        self._sync_thread.finished.connect(self._sync_thread.deleteLater)
        self._sync_thread.start()

    def _on_push_finished(self, summary: SyncSummary) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        if summary.conflicts > 0:
            dialog = ConflictsDialog(self._conflicts_service, self)
            dialog.exec()
        self._refresh_last_sync_label()
        self._show_sync_summary_dialog("Sincronización completada", summary)

    def _on_push_failed(self, payload: object) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        error, details = self._normalize_sync_error(payload)
        self._show_sync_error_dialog(error, details)

    def _update_sync_button_state(self) -> None:
        self._sync_controller.update_sync_button_state()

    def _update_conflicts_reminder(self) -> None:
        total = self._conflicts_service.count_conflicts()
        self.conflicts_reminder_label.setVisible(total > 0)
        if total > 0:
            self.conflicts_reminder_label.setText(f"Hay {total} conflictos pendientes. Revisa antes de sincronizar.")

    def _show_sync_error_dialog(self, error: Exception, details: str | None) -> None:
        if details:
            logger.error("Detalle técnico de sincronización: %s", details)
        title = "Error de sincronización"
        icon = QMessageBox.Critical
        if isinstance(error, SheetsApiDisabledError):
            self._show_message_with_details(
                title,
                "No se pudo sincronizar.\n"
                "Causa probable: La API de Google Sheets no está habilitada en el proyecto de Google Cloud.\n"
                "Acción recomendada: Actívala en Google Cloud Console y vuelve a reintentar en 2-5 minutos.",
                None,
                icon,
                action_buttons=(("Ir a configuración", self._on_open_opciones), ("Reintentar", self._sync_controller.on_sync)),
            )
            return
        if isinstance(error, SheetsPermissionError):
            email = self._service_account_email()
            email_hint = f"{email}" if email else "la cuenta de servicio"
            self._show_message_with_details(
                title,
                "No se pudo sincronizar.\n"
                f"Causa probable: La hoja no está compartida con {email_hint}.\n"
                "Acción recomendada: Comparte la hoja con ese email como Editor.",
                None,
                icon,
                action_buttons=(("Ir a configuración", self._on_open_opciones), ("Reintentar", self._sync_controller.on_sync)),
            )
            return
        if isinstance(error, SheetsNotFoundError):
            self._show_message_with_details(
                title,
                "No se pudo sincronizar.\n"
                "Causa probable: El Spreadsheet ID/URL es inválido o la hoja no existe.\n"
                "Acción recomendada: Revisa el ID/URL en configuración y vuelve a intentarlo.",
                None,
                icon,
                action_buttons=(("Ir a configuración", self._on_open_opciones),),
            )
            return
        if isinstance(error, SheetsCredentialsError):
            self._show_message_with_details(
                title,
                "No se pudo sincronizar.\n"
                "Causa probable: La credencial JSON no es válida o no se puede leer.\n"
                "Acción recomendada: Selecciona de nuevo el archivo de credenciales en configuración.",
                None,
                icon,
                action_buttons=(("Ir a configuración", self._on_open_opciones),),
            )
            return
        if isinstance(error, SheetsRateLimitError):
            self.toast.warning(
                "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta.",
                title="Sincronización pausada",
                duration_ms=6000,
            )
            self._show_message_with_details(
                title,
                "Sincronización pausada temporalmente.\n"
                "Causa probable: Google Sheets aplicó límite de peticiones.\n"
                "Acción recomendada: Espera 1 minuto y pulsa Reintentar.",
                None,
                QMessageBox.Warning,
                action_buttons=(("Reintentar", self._sync_controller.on_sync),),
            )
            return
        if isinstance(error, SheetsConfigError):
            self._show_message_with_details(
                title,
                "No se pudo sincronizar.\n"
                "Causa probable: Falta completar la configuración de Google Sheets.\n"
                "Acción recomendada: Abre configuración, guarda credenciales e ID de hoja, y reintenta.",
                None,
                QMessageBox.Warning,
                action_buttons=(("Ir a configuración", self._on_open_opciones),),
            )
            return
        fallback_message = map_error_to_ui_message(error)
        self._show_message_with_details(
            title,
            fallback_message.as_text(),
            None,
            QMessageBox.Critical if fallback_message.severity == "blocking" else QMessageBox.Warning,
            action_buttons=(("Reintentar", self._sync_controller.on_sync),),
        )

    def _apply_sync_report(self, report) -> None:
        self._last_sync_report = report
        self._sync_attempts.append({"status": report.status, "counts": report.counts})
        counts = report.counts
        self._set_sync_status_badge(report.status)
        self.sync_source_label.setText(f"Fuente: {report.source}")
        self.sync_scope_label.setText(f"Rango: {report.scope}")
        self.sync_idempotency_label.setText(f"Evita duplicados: {report.idempotency_criteria}")
        self.sync_counts_label.setText(
            "Resumen: "
            f"Filas creadas: {counts.get('created', 0)} · "
            f"Filas actualizadas: {counts.get('updated', 0)} · "
            f"Filas omitidas: {counts.get('skipped', 0)} · "
            f"Conflictos: {counts.get('conflicts', 0)} · "
            f"Errores: {counts.get('errors', 0)}"
        )
        self.sync_panel_status.setText(
            f"Estado: intento #{len(self._sync_attempts)} · actual {self._status_to_label(report.status)} · final {self._status_to_label(report.final_status)}"
        )
        self.last_sync_metrics_label.setText(
            f"Duración: {report.duration_ms} ms · Cambios: {counts.get('created', 0) + counts.get('updated', 0)} · "
            f"Conflictos: {report.conflicts_count} · Errores: {report.error_count}"
        )
        self._refresh_sync_trend_label()
        self.go_to_sync_config_button.setVisible(report.status == "CONFIG_INCOMPLETE")
        self.sync_details_button.setEnabled(True)
        self.copy_sync_report_button.setEnabled(True)
        self.retry_failed_button.setEnabled(bool(report.errors or report.conflicts))
        self.review_conflicts_button.setText("Revisar conflictos" if report.conflicts_count > 0 else "Revisar conflictos (sin pendientes)")
        self._update_conflicts_reminder()
        persist_report(report, Path.cwd())
        self._refresh_health_and_alerts()

    def _on_show_sync_history(self) -> None:
        history = list_sync_history(Path.cwd())
        if not history:
            self.toast.info("No hay sincronizaciones históricas disponibles.", title="Histórico")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Histórico de sincronizaciones")
        dialog.resize(800, 420)
        layout = QVBoxLayout(dialog)
        table = QTreeWidget(dialog)
        table.setColumnCount(4)
        table.setHeaderLabels(["Archivo", "Sync ID", "Estado", "Intentos"])
        for path in history:
            report = load_sync_report(path)
            item = QTreeWidgetItem([path.name, report.sync_id, report.final_status, str(report.attempts)])
            item.setData(0, Qt.UserRole, str(path))
            table.addTopLevelItem(item)
        layout.addWidget(table)

        def _open_selected() -> None:
            selected = table.selectedItems()
            if not selected:
                return
            report_path = Path(selected[0].data(0, Qt.UserRole))
            self._last_sync_report = load_sync_report(report_path)
            self._show_sync_details_dialog()

        actions = QHBoxLayout()
        open_btn = QPushButton("Abrir detalle")
        open_btn.clicked.connect(_open_selected)
        copy_btn = QPushButton("Copiar informe")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(to_markdown(load_sync_report(Path(table.selectedItems()[0].data(0, Qt.UserRole))))) if table.selectedItems() else None)
        actions.addWidget(open_btn)
        actions.addWidget(copy_btn)
        layout.addLayout(actions)
        dialog.exec()

    def _show_sync_details_dialog(self) -> None:
        report = self._last_sync_report
        if report is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Detalles de sincronización")
        dialog.resize(940, 480)
        apply_modal_behavior(dialog)
        layout = QVBoxLayout(dialog)
        table = QTreeWidget(dialog)
        table.setColumnCount(6)
        table.setHeaderLabels(["Timestamp", "Sev", "Entidad", "Mensaje", "Acción sugerida", "Sección"])
        for entry in report.entries:
            item = QTreeWidgetItem(
                [entry.timestamp, entry.severity, entry.entity, entry.message, entry.suggested_action, entry.section]
            )
            table.addTopLevelItem(item)
        table.header().setStretchLastSection(True)
        layout.addWidget(table, 1)

        actions = QHBoxLayout()
        open_affected = QPushButton("Abrir solicitud afectada")
        open_affected.setProperty("variant", "secondary")
        open_affected.setEnabled(bool(report.conflicts))
        open_affected.clicked.connect(self._on_review_conflicts)
        actions.addWidget(open_affected)

        mark_review = QPushButton("Marcar para revisión")
        mark_review.setProperty("variant", "secondary")
        mark_review.setEnabled(bool(report.conflicts))
        mark_review.clicked.connect(lambda: self.toast.info("Registro marcado para revisión manual."))
        actions.addWidget(mark_review)

        retry_failed = QPushButton("Reintentar solo fallidos")
        retry_failed.setProperty("variant", "secondary")
        retry_failed.setEnabled(bool(report.errors or report.conflicts))
        retry_failed.clicked.connect(self._on_retry_failed)
        actions.addWidget(retry_failed)

        export_detail = QPushButton("Exportar detalle")
        export_detail.setProperty("variant", "secondary")
        export_detail.clicked.connect(lambda: self._on_copy_sync_report())
        actions.addWidget(export_detail)

        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(dialog.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        dialog.exec()

    def _set_sync_status_badge(self, status: str) -> None:
        self.sync_status_badge.setText(self._status_to_label(status))
        tone_map = {"OK": STATUS_PATTERNS["CONFIRMED"].tone, "RUNNING": STATUS_PATTERNS["PENDING"].tone, "OK_WARN": STATUS_PATTERNS["WARNING"].tone, "ERROR": STATUS_PATTERNS["ERROR"].tone}
        self.sync_status_badge.setProperty("tone", tone_map.get(status, "pending"))
        self.sync_status_badge.setProperty("syncStatus", status)
        style = self.sync_status_badge.style()
        if style is not None:
            style.unpolish(self.sync_status_badge)
            style.polish(self.sync_status_badge)
        self.sync_status_badge.update()
        self._update_global_context()

    def _status_from_summary(self, summary: SyncSummary) -> str:
        if summary.errors > 0:
            return "ERROR"
        if summary.conflicts_detected > 0 or summary.duplicates_skipped > 0 or summary.omitted_by_delegada > 0:
            return "OK_WARN"
        return "OK"

    @staticmethod
    def _status_to_label(status: str) -> str:
        return {
            "IDLE": "⏸ En espera",
            "RUNNING": "🕒 Pendiente · Sincronizando",
            "OK": status_badge("CONFIRMED"),
            "OK_WARN": status_badge("WARNING"),
            "ERROR": status_badge("ERROR"),
            "CONFIG_INCOMPLETE": "⛔ Error · Configuración incompleta",
        }.get(status, status)

    def _sync_source_text(self) -> str:
        config = self._sheets_service.get_config()
        if not config:
            return "Error: configura credenciales de Google Sheets"
        credentials_name = Path(config.credentials_path).name if config.credentials_path else "sin archivo"
        sheet_short = f"…{config.spreadsheet_id[-6:]}" if config.spreadsheet_id else "sin-id"
        return f"Spreadsheet {sheet_short} · credencial {credentials_name}"

    def _sync_scope_text(self) -> str:
        return "Sincronización completa de delegadas y solicitudes."

    def _sync_actor_text(self) -> str:
        persona = self._current_persona()
        return persona.nombre if persona is not None else "Delegada no seleccionada"

    def _show_sync_summary_dialog(self, title: str, summary: SyncSummary) -> None:
        last_sync = self._sync_service.get_last_sync_at()
        last_sync_text = self._format_timestamp(last_sync) if last_sync else "Nunca"
        message = (
            f"Insertadas en local: {summary.inserted_local}\n"
            f"Actualizadas en local: {summary.updated_local}\n"
            f"Insertadas en Sheets: {summary.inserted_remote}\n"
            f"Actualizadas en Sheets: {summary.updated_remote}\n"
            f"Duplicados omitidos: {summary.duplicates_skipped}\n"
            f"Omitidas por delegada: {summary.omitted_by_delegada}\n"
            f"Conflictos: {summary.conflicts_detected}\n"
            f"Errores: {summary.errors}\n"
            f"Última sincronización: {last_sync_text}"
        )
        if summary.conflicts_detected > 0 or summary.errors > 0:
            self.toast.warning(message, title=title, duration_ms=7000)
            self._show_details_dialog(title, message)
        else:
            self.toast.success(message, title=title)

    def _show_message_with_details(
        self,
        title: str,
        message: str,
        details: str | None,
        icon: QMessageBox.Icon,
        action_buttons: tuple[tuple[str, object], ...] = (),
    ) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setIcon(icon)
        dialog.setText(message)
        action_mapping: dict[object, object] = {}
        for label, callback in action_buttons:
            button = dialog.addButton(label, QMessageBox.ActionRole)
            action_mapping[button] = callback
        details_button = None
        if details:
            details_button = dialog.addButton("Ver detalles", QMessageBox.ActionRole)
        dialog.addButton("Cerrar", QMessageBox.AcceptRole)
        dialog.exec()
        clicked_button = dialog.clickedButton()
        if clicked_button in action_mapping:
            action_mapping[clicked_button]()
            return
        if details_button and dialog.clickedButton() == details_button:
            self._show_details_dialog(title, details)

    def _show_details_dialog(self, title: str, details: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        apply_modal_behavior(dialog)
        layout = QVBoxLayout(dialog)
        details_text = QPlainTextEdit()
        details_text.setReadOnly(True)
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
        dialog.resize(520, 360)
        dialog.exec()

    def _normalize_sync_error(self, payload: object) -> tuple[Exception, str | None]:
        if isinstance(payload, dict):
            error = payload.get("error")
            details = payload.get("details")
            if isinstance(error, Exception):
                return error, details
            return Exception(str(error)), details
        if isinstance(payload, Exception):
            return payload, None
        return Exception(str(payload)), None

    def _set_sync_in_progress(self, in_progress: bool) -> None:
        self._sync_in_progress = in_progress
        self.sync_status_label.setVisible(in_progress)
        self.sync_progress.setVisible(in_progress)
        if self.status_sync_label is not None:
            self.status_sync_label.setVisible(in_progress)
        if self.status_sync_progress is not None:
            self.status_sync_progress.setVisible(in_progress)
        if in_progress:
            self._sync_started_at = datetime.now().isoformat()
            self.statusBar().showMessage("Sincronizando con Google Sheets…")
            self.sync_button.setEnabled(False)
            self.simulate_sync_button.setEnabled(False)
            self.confirm_sync_button.setEnabled(False)
            self.sync_details_button.setEnabled(False)
            self.copy_sync_report_button.setEnabled(False)
            self.review_conflicts_button.setEnabled(False)
            self._set_sync_status_badge("RUNNING")
            self.sync_panel_status.setText("Estado: Pendiente · Sincronizando")
        else:
            self.statusBar().clearMessage()

    def _set_processing_state(self, in_progress: bool) -> None:
        self.primary_cta_button.setEnabled(not in_progress)
        self.confirmar_button.setEnabled(not in_progress)
        self.eliminar_button.setEnabled(not in_progress)
        self.eliminar_pendiente_button.setEnabled(not in_progress)
        if in_progress:
            self.statusBar().showMessage("Procesando…")
        elif not self._sync_in_progress:
            self.statusBar().clearMessage()

    def _show_critical_error(self, error: Exception | str) -> None:
        if isinstance(error, str):
            mapped = UiErrorMessage(
                title=error,
                probable_cause="Se produjo un problema no esperado durante la operación.",
                recommended_action="Reintentar. Si persiste, contactar con soporte.",
                severity="blocking",
            )
        else:
            mapped = map_error_to_ui_message(error)
            logger.exception(
                "Error técnico capturado en UI",
                exc_info=error,
                extra={"correlation_id": mapped.incident_id},
            )
        message = mapped.as_text()
        self.toast.error(
            message,
            title="Error",
            action_label="Ver detalle",
            action_callback=lambda: self._show_error_detail(
                titulo=mapped.title,
                mensaje=message,
                incident_id=getattr(mapped, "incident_id", None),
                correlation_id=getattr(mapped, "incident_id", None),
                stack=str(error),
            ),
        )
        QMessageBox.critical(self, mapped.title, message)

    def _show_error_detail(
        self,
        *,
        titulo: str,
        mensaje: str,
        incident_id: str | None = None,
        correlation_id: str | None = None,
        stack: str | None = None,
    ) -> None:
        payload = {
            "mensaje": mensaje,
            "incident_id": incident_id or "N/D",
            "correlation_id": correlation_id or "N/D",
            "resumen": stack or "Sin detalle técnico",
        }
        dialog = HistoricoDetalleDialog(payload, self)
        dialog.setWindowTitle(titulo)
        dialog.exec()

    def _show_optional_notice(self, key: str, title: str, message: str) -> None:
        if bool(self._settings.value(key, False, type=bool)):
            self.toast.info(message, title=title)
            return
        dialog = OptionalConfirmDialog(title, message, self)
        dialog.exec()
        if dialog.skip_next_check.isChecked():
            self._settings.setValue(key, True)
        self.toast.info(message, title=title)

    def _notify_historico_filter_if_hidden(self, solicitudes_insertadas: list[SolicitudDTO]) -> None:
        inserted_ids = {solicitud.id for solicitud in solicitudes_insertadas if solicitud.id is not None}
        if not inserted_ids:
            return
        visibles_ids: set[int] = set()
        for row in range(self.historico_proxy_model.rowCount()):
            proxy_index = self.historico_proxy_model.index(row, 0)
            source_index = self.historico_proxy_model.mapToSource(proxy_index)
            solicitud = self.historico_model.solicitud_at(source_index.row())
            if solicitud and solicitud.id is not None:
                visibles_ids.add(solicitud.id)
        if inserted_ids.issubset(visibles_ids):
            return
        logger.info(
            "Solicitudes insertadas en histórico pero no visibles por filtros actuales: ids=%s",
            sorted(inserted_ids - visibles_ids),
        )
        self._show_optional_notice(
            "confirmaciones/no_visible_filtros",
            "Solicitud confirmada",
            "Solicitud confirmada. Ajusta filtros para verla en Histórico.",
        )

    def _update_pending_totals(self) -> None:
        persona = self._current_persona()
        total_min = 0
        if persona is not None and self._pending_solicitudes:
            try:
                total_min = self._solicitud_use_cases.sumar_pendientes_min(persona.id or 0, self._pending_solicitudes)
            except BusinessRuleError:
                total_min = 0
        formatted = self._format_minutes(total_min)
        self.total_pendientes_label.setText(f"Total: {formatted}")
        if self.status_pending_label is not None:
            self.status_pending_label.setText(f"Pendiente: {formatted}")
        self.statusBar().showMessage(f"Pendiente: {formatted}", 4000)

    def _service_account_email(self) -> str | None:
        config = self._sheets_service.get_config()
        if not config or not config.credentials_path:
            return None
        try:
            payload = json.loads(Path(config.credentials_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return str(payload.get("client_email", "")).strip() or None

    def _on_generar_pdf_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        selected = self._selected_historico_solicitudes()
        if not selected:
            self.toast.info("No hay solicitudes para exportar.", title="Histórico")
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(selected)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF histórico")
            self._show_critical_error(exc)
            return
        def _generate_preview(target: Path) -> Path:
            with OperationContext("exportar_historico_pdf") as operation:
                log_event(
                    logger,
                    "exportar_historico_pdf_started",
                    {"persona_id": persona.id or 0, "count": len(selected)},
                    operation.correlation_id,
                )
                pdf = self._solicitud_use_cases.generar_pdf_historico(
                    selected, target, correlation_id=operation.correlation_id
                )
                log_event(logger, "exportar_historico_pdf_finished", {"path": str(pdf)}, operation.correlation_id)
                return pdf

        try:
            preview = PdfPreviewDialog(_generate_preview, default_name, self)
            result = preview.exec()
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            if isinstance(exc, OSError):
                log_operational_error(
                    logger,
                    "File export failed during PDF preview",
                    exc=exc,
                    extra={"operation": "exportar_historico_pdf", "persona_id": persona.id or 0},
                )
            else:
                logger.exception("Error generando previsualización de PDF histórico")
            self._show_critical_error(exc)
            return
        if result == QDialog.DialogCode.Accepted:
            self._show_optional_notice(
                "confirmaciones/export_pdf_ok",
                "Exportación",
                "Exportación PDF OK",
            )

    def _on_eliminar(self) -> None:
        logger.info("CLICK eliminar_historico handler=_on_eliminar selected=%s", len(self._selected_historico_solicitudes()))
        seleccionadas = [sol for sol in self._selected_historico_solicitudes() if sol.id is not None]
        if not seleccionadas:
            logger.info("_on_eliminar early_return motivo=sin_seleccion")
            return
        try:
            self._set_processing_state(True)
            for solicitud in seleccionadas:
                with OperationContext("eliminar_solicitud") as operation:
                    self._solicitud_use_cases.eliminar_solicitud(
                        solicitud.id or 0, correlation_id=operation.correlation_id
                    )
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error eliminando solicitud")
            self._show_critical_error(exc)
            return
        finally:
            self._set_processing_state(False)
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self.notifications.notify_operation(
            OperationFeedback(
                title="Solicitudes eliminadas",
                happened="Las solicitudes seleccionadas se eliminaron del histórico.",
                affected_count=len(seleccionadas),
                incidents="Sin incidencias.",
                next_step="Puedes continuar o revisar histórico.",
            )
        )

    def _on_remove_pendiente(self) -> None:
        logger.info("CLICK eliminar_pendiente handler=_on_remove_pendiente")
        self._dump_estado_pendientes("click_eliminar_pendiente")
        selection = self.pendientes_table.selectionModel().selectedRows()
        if not selection:
            logger.info("_on_remove_pendiente early_return motivo=sin_seleccion")
            return
        logger.info(
            "Se pide confirmación de borrado motivo=policy=always_confirm selection_count>0 (instrumentación)",
        )
        rows = sorted((index.row() for index in selection), reverse=True)
        ids_to_delete: list[int] = []
        for row in rows:
            if 0 <= row < len(self._pending_solicitudes):
                solicitud = self._pending_solicitudes[row]
                if solicitud.id is not None:
                    ids_to_delete.append(solicitud.id)
        try:
            self._set_processing_state(True)
            for solicitud_id in ids_to_delete:
                with OperationContext("eliminar_pendiente") as operation:
                    self._solicitud_use_cases.eliminar_solicitud(
                        solicitud_id, correlation_id=operation.correlation_id
                    )
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error eliminando pendiente")
            self._show_critical_error(exc)
            return
        finally:
            self._set_processing_state(False)
        self._reload_pending_views()
        self._refresh_saldos()
        self.notifications.notify_operation(
            OperationFeedback(
                title="Pendientes eliminadas",
                happened="Las solicitudes pendientes seleccionadas se eliminaron.",
                affected_count=len(ids_to_delete),
                incidents="Sin incidencias.",
                next_step="Puedes añadir nuevas solicitudes o confirmar otras pendientes.",
            )
        )

    def _refresh_historico(self) -> None:
        solicitudes: list[SolicitudDTO] = []
        for persona in self._personas:
            if persona.id is None:
                continue
            solicitudes.extend(self._solicitud_use_cases.listar_solicitudes_por_persona(persona.id))
        self.historico_model.set_solicitudes(solicitudes)
        self.historico_table.sortByColumn(0, Qt.DescendingOrder)
        self._apply_historico_filters()
        self._update_action_state()

    def _refresh_saldos(self) -> None:
        filtro = self._current_saldo_filtro()
        self._update_periodo_label()
        persona = self._current_persona()
        if persona is None:
            self._set_saldos_labels(None)
            return
        try:
            resumen = self._solicitud_use_cases.calcular_resumen_saldos(persona.id or 0, filtro)
        except BusinessRuleError as exc:
            self.toast.warning(str(exc), title="Validación")
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(resumen)

    def _update_periodo_label(self) -> None:
        self.saldos_card.update_periodo_label("Mensual")

    def _set_saldos_labels(
        self,
        resumen,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
    ) -> None:
        self.saldos_card.update_saldos(resumen, pendientes_periodo, pendientes_ano)

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _on_open_historico_detalle(self) -> None:
        solicitud = self._selected_historico()
        if solicitud is None:
            return
        estado = status_badge("CONFIRMED") if solicitud.generated else status_badge("PENDING")
        payload = {
            "ID": str(solicitud.id or "-"),
            "Delegada": self.historico_model.persona_name_for_id(solicitud.persona_id) or str(solicitud.persona_id),
            "Fecha solicitada": solicitud.fecha_solicitud,
            "Fecha pedida": solicitud.fecha_pedida,
            "Desde": solicitud.desde or "-",
            "Hasta": solicitud.hasta or "-",
            "Completo": "Sí" if solicitud.completo else "No",
            "Horas": str(solicitud.horas),
            "Estado": estado,
            "Observaciones": solicitud.observaciones or "",
            "Notas": solicitud.notas or "",
        }
        dialog = HistoricoDetalleDialog(payload, self)
        dialog.exec()

    def _on_resync_historico(self) -> None:
        selected_count = len(self._selected_historico_solicitudes())
        if selected_count == 0:
            return
        self.toast.info(
            f"Re-sincronización preparada para {selected_count} solicitud(es). Ejecuta Sincronizar para completar.",
            title="Histórico",
        )

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        periodo_base = self.fecha_input.date() if hasattr(self, "fecha_input") else QDate.currentDate()
        return PeriodoFiltro.mensual(periodo_base.year(), periodo_base.month())

    def _pending_minutes_for_period(self, filtro: PeriodoFiltro) -> int:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return 0
        pendientes_filtrados = []
        for solicitud in self._pending_solicitudes:
            fecha = datetime.strptime(solicitud.fecha_pedida, "%Y-%m-%d")
            if fecha.year != filtro.year:
                continue
            if filtro.modo == "MENSUAL" and fecha.month != filtro.month:
                continue
            pendientes_filtrados.append(solicitud)
        if not pendientes_filtrados:
            return 0
        try:
            return self._solicitud_use_cases.sumar_pendientes_min(
                persona.id or 0, pendientes_filtrados
            )
        except BusinessRuleError:
            return 0

    def _clear_pendientes(self) -> None:
        self._pending_solicitudes = []
        self._pending_all_solicitudes = []
        self._hidden_pendientes = []
        self._orphan_pendientes = []
        self.pendientes_model.clear()
        self.huerfanas_model.clear()
        self._pending_conflict_rows = set()
        self._update_pending_totals()
        self._update_action_state()

    def _on_toggle_ver_todas_pendientes(self, checked: bool) -> None:
        self._pending_view_all = checked
        self.ver_todas_pendientes_button.setText("Ver solo delegada" if checked else "Ver todas")
        self._reload_pending_views()

    def _reload_pending_views(self) -> None:
        persona = self._current_persona()
        self._pending_all_solicitudes = list(self._solicitud_use_cases.listar_pendientes_all())
        if self._pending_view_all:
            self._pending_solicitudes = list(self._pending_all_solicitudes)
        elif persona is None:
            self._pending_solicitudes = []
        else:
            self._pending_solicitudes = list(self._solicitud_use_cases.listar_pendientes_por_persona(persona.id or 0))

        pending_visible_ids = {solicitud.id for solicitud in self._pending_solicitudes if solicitud.id is not None}
        self._hidden_pendientes = [
            solicitud
            for solicitud in self._pending_all_solicitudes
            if solicitud.id is not None and solicitud.id not in pending_visible_ids
        ]
        hidden_count = len(self._hidden_pendientes)
        should_warn_hidden = hidden_count > 0 and not self._pending_view_all
        self.pending_filter_warning.setVisible(should_warn_hidden)
        self.revisar_ocultas_button.setVisible(should_warn_hidden)
        if should_warn_hidden:
            self.pending_filter_warning.setText(f"Hay pendientes en otras delegadas: {hidden_count}")
            self.revisar_ocultas_button.setText(f"Revisar pendientes ocultas ({hidden_count})")
            logger.warning(
                "Pendientes no visibles por filtro actual delegada_id=%s hidden=%s",
                persona.id if persona is not None else None,
                hidden_count,
            )
        else:
            self.pending_filter_warning.setText("")

        self._orphan_pendientes = list(self._solicitud_use_cases.listar_pendientes_huerfanas())
        self.huerfanas_model.set_solicitudes(self._orphan_pendientes)
        has_orphans = bool(self._orphan_pendientes)
        self.huerfanas_label.setVisible(has_orphans)
        self.huerfanas_table.setVisible(has_orphans)
        self.eliminar_huerfana_button.setVisible(has_orphans)

        if persona is not None:
            logger.info(
                "Cambio delegada id=%s pendientes_delegada=%s pendientes_totales=%s",
                persona.id,
                len(list(self._solicitud_use_cases.listar_pendientes_por_persona(persona.id or 0))),
                len(list(self._solicitud_use_cases.listar_pendientes_all())),
            )

        self._refresh_pending_ui_state()

    def _on_review_hidden_pendientes(self) -> None:
        if not self._hidden_pendientes:
            return
        first_hidden = self._hidden_pendientes[0]
        self.ver_todas_pendientes_button.setChecked(True)
        self._reload_pending_views()
        self._focus_pending_by_id(first_hidden.id)

    def _on_remove_huerfana(self) -> None:
        selection = self.huerfanas_table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        if row < 0 or row >= len(self._orphan_pendientes):
            return
        solicitud = self._orphan_pendientes[row]
        if solicitud.id is None:
            return
        self._solicitud_use_cases.eliminar_solicitud(solicitud.id)
        self._reload_pending_views()

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )
