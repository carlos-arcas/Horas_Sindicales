from __future__ import annotations

import logging
from pathlib import Path

try:
    from PySide6.QtCore import QDate, QEvent, QItemSelectionModel, QObject, QSettings, QThread, QTime, QTimer, Qt
    # `QKeyEvent` vive en QtGui en PySide6 (no en QtCore); importarlo aquí evita NameError en eventFilter.
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFrame,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QTableView,
        QTextEdit,
        QTimeEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except Exception:  # pragma: no cover - habilita import en entornos CI sin Qt
    class _QtFallbackBase:
        pass

    QDate = QEvent = QItemSelectionModel = QObject = QSettings = QThread = QTime = QTimer = Qt = object
    QKeyEvent = object
    QCheckBox = QComboBox = QDateEdit = QDialog = QFileDialog = QHBoxLayout = QLabel = object
    QMainWindow = type("QMainWindow", (_QtFallbackBase,), {})
    QMessageBox = QPushButton = QApplication = QAbstractItemView = QPlainTextEdit = object
    QFrame = QHeaderView = QProgressBar = QSizePolicy = QSplitter = QTableView = QTimeEdit = object
    QVBoxLayout = QWidget = QDialogButtonBox = QTextEdit = QTreeWidget = QTreeWidgetItem = object

from app.application.conflicts_service import ConflictsService
from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases.conflict_resolution_policy import ConflictResolutionPolicy
from app.application.use_cases.retry_sync_use_case import RetrySyncUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.validacion_preventiva_lock_use_case import ValidacionPreventivaLockUseCase
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncSummary
from app.ui.copy_catalog import copy_text
try:
    from app.ui.conflicts_dialog import ConflictsDialog
    from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
    from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
    from app.ui.patterns import apply_modal_behavior, build_modal_actions, status_badge, STATUS_PATTERNS
    from app.ui.widgets.toast import ToastManager
    from app.ui.controllers.personas_controller import PersonasController
    from app.ui.controllers.solicitudes_controller import SolicitudesController
    from app.ui.controllers.sync_controller import SyncController
    from app.ui.controllers.pdf_controller import PdfController
    from app.ui.notification_service import ConfirmationSummaryPayload, NotificationService, OperationFeedback
    from app.ui.toast_helpers import toast_error, toast_success
    from app.ui.components.saldos_card import SaldosCard
    from app.ui.sync_reporting import (build_config_incomplete_report, build_failed_report, build_simulation_report,
                                       build_sync_report, list_sync_history, load_sync_report, persist_report,
                                       to_markdown)
    from app.ui.workers.sincronizacion_workers import PushWorker
    from app.ui.vistas.main_window_health_mixin import MainWindowHealthMixin
    from app.ui.vistas.init_refresh import run_init_refresh
    from app.ui.vistas.builders.main_window_builders import build_main_window_widgets, build_shell_layout, build_status_bar
    from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf
    from app.ui.vistas.confirmacion_actions import (ask_push_after_pdf, build_confirmation_payload,
                                                    execute_confirmar_with_pdf, finalize_confirmar_with_pdf,
                                                    iterar_pendientes_en_tabla, on_confirmar, on_insertar_sin_pdf,
                                                    prompt_confirm_pdf_path, show_confirmation_closure,
                                                    show_pdf_actions_dialog, sum_solicitudes_minutes,
                                                    undo_confirmation)
    from app.ui.vistas import historico_actions
    from app.ui.vistas.ui_helpers import abrir_archivo_local
    from app.ui.vistas.main_window_helpers import (build_estado_pendientes_debug_payload,
                                                   build_historico_filters_payload,
                                                   handle_historico_render_mismatch, log_estado_pendientes,
                                                   show_sync_error_dialog_from_exception)
    from app.ui.vistas.main_window import acciones_pendientes, validacion_preventiva
    from app.ui.vistas.solicitudes_presenter import ActionStateInput, build_action_state
except Exception:  # pragma: no cover - habilita import parcial sin dependencias de UI/Qt
    def _qt_unavailable(*args, **kwargs):
        raise RuntimeError("UI no disponible: falta instalación de Qt/PySide6")

    ConflictsDialog = GrupoConfigDialog = PdfConfigDialog = ToastManager = object
    ActionStateInput = object
    build_action_state = _qt_unavailable
    validacion_preventiva = object
    PersonasController = SolicitudesController = SyncController = PdfController = object
    ConfirmationSummaryPayload = NotificationService = OperationFeedback = object
    SaldosCard = PushWorker = object
    MainWindowHealthMixin = type("MainWindowHealthMixin", (), {})
    UiErrorMessage = object
    map_error_to_ui_message = _qt_unavailable
    apply_modal_behavior = build_modal_actions = status_badge = _qt_unavailable
    STATUS_PATTERNS = {}
    toast_error = toast_success = _qt_unavailable
    build_config_incomplete_report = build_failed_report = build_simulation_report = _qt_unavailable
    build_sync_report = list_sync_history = load_sync_report = persist_report = to_markdown = _qt_unavailable
    run_init_refresh = build_main_window_widgets = build_shell_layout = build_status_bar = _qt_unavailable
    debe_habilitar_confirmar_pdf = ask_push_after_pdf = build_confirmation_payload = _qt_unavailable
    execute_confirmar_with_pdf = finalize_confirmar_with_pdf = iterar_pendientes_en_tabla = _qt_unavailable
    on_confirmar = on_insertar_sin_pdf = prompt_confirm_pdf_path = _qt_unavailable
    show_confirmation_closure = show_pdf_actions_dialog = sum_solicitudes_minutes = undo_confirmation = _qt_unavailable
    class _HistoricoActionsFallback:
        def __getattr__(self, _name):
            return _qt_unavailable

    historico_actions = _HistoricoActionsFallback()
    abrir_archivo_local = _qt_unavailable
    build_estado_pendientes_debug_payload = build_historico_filters_payload = _qt_unavailable
    handle_historico_render_mismatch = log_estado_pendientes = show_sync_error_dialog_from_exception = _qt_unavailable
from . import acciones_personas, acciones_sincronizacion, data_refresh, form_handlers, layout_builder, wiring
from app.core.observability import OperationContext
from app.bootstrap.logging import log_operational_error

from .layout_builder import HistoricoDetalleDialog, OptionalConfirmDialog, PdfPreviewDialog
try:
    from .state_helpers import resolve_active_delegada_id, set_processing_state, update_action_state
    from .state_actions import MainWindowStateActionsMixin
    from .state_validations import MainWindowStateValidationMixin
    from .state_bindings import registrar_state_bindings
except Exception:  # pragma: no cover
    class MainWindowStateActionsMixin:
        pass

    class MainWindowStateValidationMixin:
        pass

    def registrar_state_bindings(_cls) -> None:
        return

    def set_processing_state(_window, _in_progress: bool) -> None:
        return

    def update_action_state(_window) -> None:
        return

    def resolve_active_delegada_id(_delegada_ids: list[int], _preferred_id: object) -> int | None:
        return None
logger = logging.getLogger(__name__)
TAB_HISTORICO = 1

class MainWindow(MainWindowStateActionsMixin, MainWindowStateValidationMixin, MainWindowHealthMixin, QMainWindow):
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
        validacion_preventiva_lock_use_case: ValidacionPreventivaLockUseCase | None = None,
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
        self._validacion_preventiva_lock_use_case = (
            validacion_preventiva_lock_use_case or ValidacionPreventivaLockUseCase()
        )
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
        self._solicitudes_runtime_error = False
        self._solicitudes_last_action_saved = False
        self.status_sync_label: QLabel | None = None
        self.status_sync_progress: QProgressBar | None = None
        self.status_pending_label: QLabel | None = None
        self.saldos_card: SaldosCard | None = None
        self.horas_input: object | None = None
        self.sidebar: QFrame | None = None
        self.stacked_pages: QWidget | None = None
        self.page_historico: QWidget | None = None
        self.page_configuracion: QWidget | None = None
        self.page_sincronizacion: QWidget | None = None
        self.page_solicitudes: QWidget | None = None
        self.solicitudes_splitter: QSplitter | None = None
        self.sidebar_buttons: list[QPushButton] = []
        self._sidebar_routes: list[dict[str, int | None]] = []
        self._active_sidebar_index = 0
        # Placeholders explícitos para contratos de inicialización self.* en tests estáticos.
        self.main_tabs = None
        self.persona_combo = self.fecha_input = self.desde_input = self.hasta_input = None
        self.desde_container = self.hasta_container = None
        self.desde_placeholder = self.hasta_placeholder = None
        self.completo_check = self.notas_input = None
        self.pending_errors_frame = self.pending_errors_summary = None
        self.show_help_toggle = None
        self.solicitudes_status_label = self.solicitudes_status_hint = None
        self.solicitudes_tip_1 = self.solicitudes_tip_2 = self.solicitudes_tip_3 = None
        self.solicitud_inline_error = self.delegada_field_error = self.fecha_field_error = self.tramo_field_error = None
        self.insertar_sin_pdf_button = self.confirmar_button = None
        self.agregar_button = self.eliminar_pendiente_button = self.eliminar_huerfana_button = None
        self.revisar_ocultas_button = self.ver_todas_pendientes_button = None
        self.total_pendientes_label = self.pending_filter_warning = None
        self.pendientes_table = self.huerfanas_table = None
        self.pendientes_model = self.huerfanas_model = None
        self.huerfanas_label = None
        self.sync_button = self.confirm_sync_button = None
        self.retry_failed_button = self.simulate_sync_button = self.review_conflicts_button = None
        self.go_to_sync_config_button = self.copy_sync_report_button = None
        self.sync_progress = self.sync_panel_status = None
        self.sync_status_label = self.sync_status_badge = None
        self.sync_counts_label = self.sync_details_button = None
        self.sync_source_label = self.sync_scope_label = self.sync_idempotency_label = None
        self.last_sync_metrics_label = self.conflicts_reminder_label = None
        self.historico_search_input = self.historico_estado_combo = self.historico_delegada_combo = None
        self.historico_desde_date = self.historico_hasta_date = None
        self.historico_apply_filters_button = None
        self.historico_todas_delegadas_check = None
        self.historico_periodo_anual_radio = self.historico_periodo_mes_radio = self.historico_periodo_rango_radio = None
        self.historico_periodo_anual_spin = self.historico_periodo_mes_ano_spin = self.historico_periodo_mes_combo = None
        self.historico_table = self.historico_model = self.historico_proxy_model = None
        self.historico_empty_state = self.historico_details_content = None
        self.open_saldos_modal_button = None
        self.generar_pdf_button = self.eliminar_button = None
        self.historico_select_all_visible_check = self.historico_sync_button = None
        self.historico_export_hint_label = None
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
        self._pdf_preview_dialog_class = PdfPreviewDialog
        self._historico_detalle_dialog_class = HistoricoDetalleDialog
        self._optional_confirm_dialog_class = OptionalConfirmDialog
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self._apply_help_preferences()
        self._apply_solicitudes_tooltips()
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
        self._post_init_load()
        QTimer.singleShot(0, self._warmup_sync_client)

    def _warmup_sync_client(self) -> None:
        try:
            if hasattr(self._sync_service, "ensure_connection"):
                self._sync_service.ensure_connection()
        except Exception as exc:  # pragma: no cover - warmup no debe bloquear la UI
            log_operational_error(
                logger,
                "SYNC_WARMUP_FAILED",
                exc=exc,
                extra={"operation": "sync_warmup"},
            )

    def _post_init_load(self) -> None:
        run_init_refresh(
            refresh_resumen=self._refresh_saldos,
            refresh_pendientes=self._reload_pending_views,
            refresh_historico=lambda: self._refresh_historico(force=True),
            emit_log=logger.info,
        )

    def _init_refresh(self) -> None:
        self._post_init_load()

    def _on_main_tab_changed(self, index: int) -> None:
        if index != TAB_HISTORICO:
            return
        if not (self.historico_desde_date.date().isValid() and self.historico_hasta_date.date().isValid()):
            self._apply_historico_last_30_days()
        self._refresh_historico(force=False)

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

        if title.strip():
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
        wiring.build_ui(self)

    def _build_layout(self) -> None:
        layout_builder.build_layout_phase(self)

    def _wire_signals(self) -> None:
        wiring.wire_signals_phase(self)

    def _apply_initial_state(self) -> None:
        layout_builder.apply_initial_state_phase(self)

    def _create_widgets(self) -> None:
        layout_builder.create_widgets(self)

    def _build_shell_layout(self) -> None:
        layout_builder.build_shell(self)

    def _switch_sidebar_page(self, index: int) -> None:
        if self.main_tabs is not None and 0 <= index <= 2:
            self.main_tabs.setCurrentIndex(index)

    def _build_status_bar(self) -> None:
        layout_builder.build_status(self)

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
                    if self.agregar_button.isEnabled():
                        self.agregar_button.click()
                    else:
                        logger.info("eventFilter early_return motivo=agregar_button_disabled")
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



registrar_state_bindings(MainWindow)
