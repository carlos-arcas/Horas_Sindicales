from __future__ import annotations

import logging
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QDate, QEvent, QSettings, QTime, QTimer, QUrl, Qt, QObject, Signal, Slot, QThread
from PySide6.QtGui import QDesktopServices, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QApplication,
    QAbstractItemView,
    QPlainTextEdit,
    QGridLayout,
    QFrame,
    QHeaderView,
    QProgressBar,
    QSizePolicy,
    QScrollArea,
    QStatusBar,
    QTabWidget,
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
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_utils import minutes_to_hhmm
from app.domain.request_time import validate_request_inputs
from app.domain.sync_models import Alert, HealthReport, SyncAttemptReport, SyncExecutionPlan, SyncSummary
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsConfigError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)
from app.ui.models_qt import SolicitudesTableModel
from app.ui.historico_view import ESTADOS_HISTORICO, HistoricalViewModel
from app.ui.conflicts_dialog import ConflictsDialog
from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
from app.ui.person_dialog import PersonaDialog
from app.ui.style import apply_theme
from app.ui.patterns import apply_modal_behavior, build_modal_actions, status_badge, STATUS_PATTERNS
from app.ui.widgets.header import HeaderWidget
from app.ui.widgets.toast import ToastManager
from app.ui.controllers.personas_controller import PersonasController
from app.ui.controllers.solicitudes_controller import SolicitudesController
from app.ui.controllers.sync_controller import SyncController
from app.ui.controllers.pdf_controller import PdfController
from app.ui.notification_service import ConfirmationSummaryPayload, NotificationService, OperationFeedback
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

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    PDF_PREVIEW_AVAILABLE = True
except ImportError:  # pragma: no cover - depende de instalación local
    QPdfDocument = None
    QPdfView = None
    PDF_PREVIEW_AVAILABLE = False

logger = logging.getLogger(__name__)


class SyncWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.sync_bidirectional()
        except Exception as exc:
            logger.exception("Error durante la sincronización")
            self.failed.emit(
                {
                    "error": exc,
                    "details": traceback.format_exc(),
                }
            )
            return
        self.finished.emit(summary)


class PushWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.push()
        except Exception as exc:
            logger.exception("Error durante la subida")
            self.failed.emit(
                {
                    "error": exc,
                    "details": traceback.format_exc(),
                }
            )
            return
        self.finished.emit(summary)


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
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(generated)))

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

        apply_modal_behavior(self, primary_button=save_as)


class MainWindow(QMainWindow):
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
        app = QApplication.instance()
        if app:
            apply_theme(app)
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
    ) -> None:
        content.setVisible(False)
        button.setCheckable(True)

        def _toggle(checked: bool) -> None:
            content.setVisible(checked)
            button.setText(expanded_text if checked else collapsed_text)

        button.toggled.connect(_toggle)
        _toggle(False)

    def _build_saldos_card(self) -> QFrame:
        saldos_card, saldos_layout = self._create_card("Saldos detallados")
        self.saldos_details_button = QPushButton("Ver detalles")
        self.saldos_details_button.setProperty("variant", "secondary")
        saldos_layout.addWidget(self.saldos_details_button)

        self.saldos_details_content = QWidget()
        saldos_details_layout = QVBoxLayout(self.saldos_details_content)
        saldos_details_layout.setContentsMargins(0, 0, 0, 0)
        saldos_details_layout.setSpacing(8)

        saldos_grid = QGridLayout()
        saldos_grid.setHorizontalSpacing(10)
        saldos_grid.setVerticalSpacing(8)

        saldos_grid.addWidget(QLabel(""), 0, 0)
        consumidas_header = QLabel("Consumidas")
        consumidas_header.setProperty("role", "secondary")
        saldos_grid.addWidget(consumidas_header, 0, 1)
        restantes_header = QLabel("Restantes")
        restantes_header.setProperty("role", "secondary")
        saldos_grid.addWidget(restantes_header, 0, 2)

        self.saldo_periodo_consumidas = self._build_saldo_field()
        self.saldo_periodo_restantes = self._build_saldo_field()
        self.saldo_anual_consumidas = self._build_saldo_field()
        self.saldo_anual_restantes = self._build_saldo_field()
        self.saldo_grupo_consumidas = self._build_saldo_field()
        self.saldo_grupo_restantes = self._build_saldo_field()

        self.saldo_periodo_label = QLabel("Mensual")
        saldos_grid.addWidget(self.saldo_periodo_label, 1, 0)
        saldos_grid.addWidget(self.saldo_periodo_consumidas, 1, 1)
        saldos_grid.addWidget(self.saldo_periodo_restantes, 1, 2)

        saldos_grid.addWidget(QLabel("Anual delegada"), 2, 0)
        saldos_grid.addWidget(self.saldo_anual_consumidas, 2, 1)
        saldos_grid.addWidget(self.saldo_anual_restantes, 2, 2)

        saldos_grid.addWidget(QLabel("Anual grupo"), 3, 0)
        saldos_grid.addWidget(self.saldo_grupo_consumidas, 3, 1)
        saldos_grid.addWidget(self.saldo_grupo_restantes, 3, 2)
        saldos_details_layout.addLayout(saldos_grid)

        self.exceso_badge = QLabel("")
        self.exceso_badge.setProperty("role", "badge")
        self.exceso_badge.setVisible(False)
        exceso_row = QHBoxLayout()
        exceso_row.addStretch(1)
        exceso_row.addWidget(self.exceso_badge)
        saldos_details_layout.addLayout(exceso_row)

        bolsas_separator = QFrame()
        bolsas_separator.setProperty("role", "subtleSeparator")
        bolsas_separator.setFixedHeight(1)
        saldos_details_layout.addWidget(bolsas_separator)

        bolsas_grid = QGridLayout()
        bolsas_grid.setHorizontalSpacing(8)
        bolsas_grid.setVerticalSpacing(6)
        bolsas_grid.addWidget(QLabel("Bolsa mensual delegada"), 0, 0)
        self.bolsa_mensual_label = QLabel("00:00")
        self.bolsa_mensual_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_mensual_label, 0, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual delegada"), 1, 0)
        self.bolsa_delegada_label = QLabel("00:00")
        self.bolsa_delegada_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_delegada_label, 1, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual grupo"), 2, 0)
        self.bolsa_grupo_label = QLabel("00:00")
        self.bolsa_grupo_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_grupo_label, 2, 1)
        saldos_details_layout.addLayout(bolsas_grid)
        saldos_layout.addWidget(self.saldos_details_content)
        self._configure_disclosure(self.saldos_details_button, self.saldos_details_content)
        return saldos_card

    def _build_ui(self) -> None:
        self.persona_combo = QComboBox()
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_frame = QFrame()
        header_frame.setProperty("role", "header")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        header = HeaderWidget()
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        header_layout.addWidget(header)

        header_separator = QFrame()
        header_separator.setObjectName("headerSeparator")
        header_separator.setFixedHeight(3)
        header_layout.addWidget(header_separator)
        layout.addWidget(header_frame)

        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("mainTabs")
        self.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.main_tabs, 1)

        operativa_tab = QWidget()
        operativa_layout = QVBoxLayout(operativa_tab)
        operativa_layout.setContentsMargins(0, 0, 0, 0)
        operativa_layout.setSpacing(12)
        operativa_help = QLabel("Completa la solicitud y confirma solo cuando estés lista.")
        operativa_help.setWordWrap(True)
        operativa_help.setProperty("role", "secondary")
        operativa_layout.addWidget(operativa_help)

        # UX: Operativa concentra solo tareas diarias (alta + pendientes + confirmación)
        # para reducir cambios de contexto y evitar mezclar navegación histórica.
        self._content_row = QBoxLayout(QBoxLayout.LeftToRight)
        self._content_row.setSpacing(14)
        operativa_layout.addLayout(self._content_row, 1)

        left_column = QVBoxLayout()
        left_column.setSpacing(14)
        self._content_row.addLayout(left_column, 3)

        solicitud_card, solicitud_layout = self._create_card("Alta de solicitud")
        solicitud_layout.setSpacing(12)

        self.stepper_labels: list[QLabel] = []
        self._step_bullets: list[QLabel] = []
        self._step_titles = [
            "Completar datos",
            "Revisar pendientes",
            "Confirmar",
        ]
        stepper_layout = QHBoxLayout()
        stepper_layout.setSpacing(8)
        stepper_layout.setContentsMargins(0, 0, 0, 0)
        for step_text in self._step_titles:
            step_container = QFrame()
            step_container.setProperty("role", "stepContainer")
            step_container.setFixedHeight(30)
            step_container_layout = QHBoxLayout(step_container)
            step_container_layout.setContentsMargins(8, 4, 8, 4)
            step_container_layout.setSpacing(6)

            bullet = QLabel("1")
            bullet.setProperty("role", "stepBulletIdle")
            self._step_bullets.append(bullet)
            step_container_layout.addWidget(bullet)

            step_label = QLabel(step_text)
            step_label.setProperty("role", "stepIdle")
            self.stepper_labels.append(step_label)
            step_container_layout.addWidget(step_label)

            stepper_layout.addWidget(step_container)
        stepper_layout.addStretch(1)
        solicitud_layout.addLayout(stepper_layout)

        self.stepper_context_label = QLabel("Completa los datos obligatorios")
        self.stepper_context_label.setProperty("role", "secondary")
        solicitud_layout.addWidget(self.stepper_context_label)

        self.confirmation_summary_label = QLabel("")
        self.confirmation_summary_label.setProperty("role", "secondary")
        self.confirmation_summary_label.setVisible(False)
        self.confirmation_summary_label.setWordWrap(True)
        solicitud_layout.addWidget(self.confirmation_summary_label)

        self.pending_errors_frame = QFrame()
        self.pending_errors_frame.setProperty("role", "error")
        pending_errors_layout = QVBoxLayout(self.pending_errors_frame)
        pending_errors_layout.setContentsMargins(10, 8, 10, 8)
        pending_errors_layout.setSpacing(6)
        self.pending_errors_title = QLabel("Errores pendientes")
        self.pending_errors_title.setProperty("role", "sectionTitle")
        pending_errors_layout.addWidget(self.pending_errors_title)
        self.pending_errors_summary = QLabel("")
        self.pending_errors_summary.setWordWrap(True)
        pending_errors_layout.addWidget(self.pending_errors_summary)
        self.goto_existing_button = QPushButton("Ir a la existente")
        self.goto_existing_button.setProperty("variant", "ghost")
        self.goto_existing_button.clicked.connect(self._on_go_to_existing_duplicate)
        self.goto_existing_button.setVisible(False)
        pending_errors_layout.addWidget(self.goto_existing_button)
        self.pending_errors_frame.setVisible(False)
        solicitud_layout.addWidget(self.pending_errors_frame)

        datos_basicos_label = QLabel("Datos básicos")
        datos_basicos_label.setProperty("role", "sectionTitle")
        solicitud_layout.addWidget(datos_basicos_label)

        solicitud_row = QHBoxLayout()
        solicitud_row.setSpacing(10)
        solicitud_row.addWidget(QLabel("Fecha"))
        self.fecha_input = QDateEdit(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.dateChanged.connect(self._on_fecha_changed)
        solicitud_row.addWidget(self.fecha_input)

        self.desde_input = QTimeEdit(QTime(9, 0))
        self.desde_input.setDisplayFormat("HH:mm")
        self.desde_input.timeChanged.connect(self._update_solicitud_preview)
        self.desde_container = QWidget()
        desde_layout = QHBoxLayout(self.desde_container)
        desde_layout.setContentsMargins(0, 0, 0, 0)
        desde_layout.setSpacing(6)
        desde_layout.addWidget(QLabel("Desde"))
        desde_layout.addWidget(self.desde_input)
        solicitud_row.addWidget(self.desde_container)

        self.desde_placeholder = QWidget()
        self.desde_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        solicitud_row.addWidget(self.desde_placeholder)

        self.hasta_input = QTimeEdit(QTime(17, 0))
        self.hasta_input.setDisplayFormat("HH:mm")
        self.hasta_input.timeChanged.connect(self._update_solicitud_preview)
        self.hasta_container = QWidget()
        hasta_layout = QHBoxLayout(self.hasta_container)
        hasta_layout.setContentsMargins(0, 0, 0, 0)
        hasta_layout.setSpacing(6)
        hasta_layout.addWidget(QLabel("Hasta"))
        hasta_layout.addWidget(self.hasta_input)
        solicitud_row.addWidget(self.hasta_container)

        self.hasta_placeholder = QWidget()
        self.hasta_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        solicitud_row.addWidget(self.hasta_placeholder)

        self.completo_check = QCheckBox("Completo")
        self.completo_check.toggled.connect(self._on_completo_changed)
        solicitud_row.addWidget(self.completo_check)

        self.total_preview_label = QLabel("Información de saldo")
        self.total_preview_label.setProperty("role", "secondary")
        solicitud_row.addWidget(self.total_preview_label)

        self.total_preview_input = QLineEdit("00:00")
        self.total_preview_input.setReadOnly(True)
        self.total_preview_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_preview_input.setMaximumWidth(84)
        solicitud_row.addWidget(self.total_preview_input)

        self.consequence_microcopy_label = QLabel("Esta acción consumirá 0 horas del saldo disponible.")
        self.consequence_microcopy_label.setProperty("role", "secondary")
        solicitud_row.addWidget(self.consequence_microcopy_label)

        self.cuadrante_warning_label = QLabel("")
        self.cuadrante_warning_label.setProperty("role", "secondary")
        self.cuadrante_warning_label.setVisible(False)
        solicitud_row.addWidget(self.cuadrante_warning_label)

        self.agregar_button = QPushButton("Añadir a pendientes")
        self.agregar_button.setProperty("variant", "secondary")
        self.agregar_button.clicked.connect(
            self._on_add_pendiente,
            Qt.ConnectionType.UniqueConnection,
        )
        solicitud_row.addWidget(self.agregar_button)
        solicitud_row.addStretch(1)
        solicitud_layout.addLayout(solicitud_row)

        validacion_label = QLabel("Validación")
        validacion_label.setProperty("role", "sectionTitle")
        solicitud_layout.addWidget(validacion_label)

        self.solicitud_inline_error = QLabel("")
        self.solicitud_inline_error.setProperty("role", "error")
        self.solicitud_inline_error.setVisible(False)
        solicitud_layout.addWidget(self.solicitud_inline_error)

        self.delegada_field_error = QLabel("")
        self.delegada_field_error.setProperty("role", "error")
        self.delegada_field_error.setVisible(False)
        solicitud_layout.addWidget(self.delegada_field_error)

        self.fecha_field_error = QLabel("")
        self.fecha_field_error.setProperty("role", "error")
        self.fecha_field_error.setVisible(False)
        solicitud_layout.addWidget(self.fecha_field_error)

        self.tramo_field_error = QLabel("")
        self.tramo_field_error.setProperty("role", "error")
        self.tramo_field_error.setVisible(False)
        solicitud_layout.addWidget(self.tramo_field_error)

        observaciones_label = QLabel("Observaciones")
        observaciones_label.setProperty("role", "sectionTitle")
        solicitud_layout.addWidget(observaciones_label)

        notas_row = QHBoxLayout()
        notas_row.setSpacing(8)
        notas_row.addWidget(QLabel("Notas"))
        self.notas_input = QPlainTextEdit()
        self.notas_input.setPlaceholderText("Notas para la solicitud")
        self.notas_input.setMinimumHeight(74)
        self.notas_input.installEventFilter(self)
        self.persona_combo.installEventFilter(self)
        self.fecha_input.installEventFilter(self)
        self.desde_input.installEventFilter(self)
        self.hasta_input.installEventFilter(self)
        self.completo_check.installEventFilter(self)
        self.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        notas_row.addWidget(self.notas_input, 1)
        solicitud_layout.addLayout(notas_row)
        left_column.addWidget(solicitud_card)

        pendientes_card, pendientes_layout = self._create_card("Pendientes de confirmar")
        self._pendientes_group = pendientes_card
        pending_tools = QHBoxLayout()
        pending_tools.setSpacing(8)
        self.ver_todas_pendientes_button = QPushButton("Ver todas")
        self.ver_todas_pendientes_button.setProperty("variant", "ghost")
        self.ver_todas_pendientes_button.setCheckable(True)
        self.ver_todas_pendientes_button.toggled.connect(self._on_toggle_ver_todas_pendientes)
        pending_tools.addWidget(self.ver_todas_pendientes_button)
        self.revisar_ocultas_button = QPushButton("Revisar pendientes ocultas")
        self.revisar_ocultas_button.setProperty("variant", "ghost")
        self.revisar_ocultas_button.setVisible(False)
        self.revisar_ocultas_button.clicked.connect(self._on_review_hidden_pendientes)
        pending_tools.addWidget(self.revisar_ocultas_button)
        self.pending_details_button = QPushButton("Ver detalles")
        self.pending_details_button.setProperty("variant", "ghost")
        pending_tools.addWidget(self.pending_details_button)
        self.pending_filter_warning = QLabel("")
        self.pending_filter_warning.setProperty("role", "secondary")
        self.pending_filter_warning.setVisible(False)
        pending_tools.addWidget(self.pending_filter_warning)
        pending_tools.addStretch(1)
        pendientes_layout.addLayout(pending_tools)

        self.pending_details_content = QWidget()
        pending_details_layout = QVBoxLayout(self.pending_details_content)
        pending_details_layout.setContentsMargins(0, 0, 0, 0)
        pending_details_layout.setSpacing(12)

        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pendientes_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.pendientes_table.selectionModel().selectionChanged.connect(self._update_action_state)
        self.pendientes_table.setShowGrid(False)
        self.pendientes_table.setAlternatingRowColors(True)
        self.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pendientes_table.setMinimumHeight(220)
        self._configure_solicitudes_table(self.pendientes_table)
        pending_details_layout.addWidget(self.pendientes_table, 1)

        self.huerfanas_label = QLabel("Reparar · Pendientes huérfanas")
        self.huerfanas_label.setProperty("role", "sectionTitle")
        self.huerfanas_label.setVisible(False)
        pending_details_layout.addWidget(self.huerfanas_label)

        self.huerfanas_table = QTableView()
        self.huerfanas_model = SolicitudesTableModel([])
        self.huerfanas_table.setModel(self.huerfanas_model)
        self.huerfanas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.huerfanas_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.huerfanas_table.setShowGrid(False)
        self.huerfanas_table.setAlternatingRowColors(True)
        self.huerfanas_table.setMinimumHeight(120)
        self._configure_solicitudes_table(self.huerfanas_table)
        self.huerfanas_table.setVisible(False)
        pending_details_layout.addWidget(self.huerfanas_table)

        footer_separator = QFrame()
        footer_separator.setProperty("role", "subtleSeparator")
        footer_separator.setFixedHeight(1)
        pending_details_layout.addWidget(footer_separator)

        pendientes_footer = QHBoxLayout()
        pendientes_footer.setSpacing(10)

        left_actions = QHBoxLayout()
        left_actions.setSpacing(8)
        self.eliminar_pendiente_button = QPushButton("Eliminar selección")
        self.eliminar_pendiente_button.setProperty("variant", "ghost")
        self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
        left_actions.addWidget(self.eliminar_pendiente_button)

        self.eliminar_huerfana_button = QPushButton("Eliminar huérfana")
        self.eliminar_huerfana_button.setProperty("variant", "ghost")
        self.eliminar_huerfana_button.clicked.connect(self._on_remove_huerfana)
        self.eliminar_huerfana_button.setVisible(False)
        left_actions.addWidget(self.eliminar_huerfana_button)

        self.insertar_sin_pdf_button = QPushButton("Confirmar sin PDF")
        self.insertar_sin_pdf_button.setProperty("variant", "secondary")
        self.insertar_sin_pdf_button.clicked.connect(self._on_insertar_sin_pdf)
        left_actions.addWidget(self.insertar_sin_pdf_button)
        pendientes_footer.addLayout(left_actions)

        pendientes_footer.addStretch(1)

        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)
        self.total_pendientes_label = QLabel("Total: 00:00")
        self.total_pendientes_label.setProperty("role", "sectionTitle")
        right_actions.addWidget(self.total_pendientes_label)

        self.abrir_pdf_check = QCheckBox("Abrir PDF")
        self.abrir_pdf_check.setChecked(True)
        right_actions.addWidget(self.abrir_pdf_check)

        self.confirmar_button = QPushButton("Confirmar y generar")
        self.confirmar_button.setProperty("variant", "secondary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        right_actions.addWidget(self.confirmar_button)

        self.primary_cta_button = QPushButton("Añadir a pendientes")
        self.primary_cta_button.setProperty("variant", "primary")
        self.primary_cta_button.setProperty("role", "dominantCta")
        self.primary_cta_button.clicked.connect(self._on_primary_cta_clicked)
        right_actions.addWidget(self.primary_cta_button)

        self.primary_cta_hint = QLabel("")
        self.primary_cta_hint.setProperty("role", "secondary")
        right_actions.addWidget(self.primary_cta_hint)

        pendientes_footer.addLayout(right_actions)
        pending_details_layout.addLayout(pendientes_footer)
        pendientes_layout.addWidget(self.pending_details_content, 1)
        self._configure_disclosure(self.pending_details_button, self.pending_details_content)
        left_column.addWidget(pendientes_card, 1)

        self.main_tabs.addTab(operativa_tab, "Operativa")

        historico_tab = QWidget()
        historico_tab_layout = QVBoxLayout(historico_tab)
        historico_tab_layout.setContentsMargins(0, 0, 0, 0)
        historico_tab_layout.setSpacing(12)
        historico_help = QLabel("Consulta histórico y saldos solo cuando necesites más contexto.")
        historico_help.setWordWrap(True)
        historico_help.setProperty("role", "secondary")
        historico_tab_layout.addWidget(historico_help)

        saldos_card = self._build_saldos_card()
        historico_tab_layout.addWidget(saldos_card)

        # UX: el histórico se separa para inspección y reporting sin contaminar el flujo operativo.
        historico_card, historico_layout = self._create_card("Histórico")
        self.historico_details_button = QPushButton("Más información")
        self.historico_details_button.setProperty("variant", "secondary")
        historico_layout.addWidget(self.historico_details_button)
        self.historico_details_content = QWidget()
        historico_details_layout = QVBoxLayout(self.historico_details_content)
        historico_details_layout.setContentsMargins(0, 0, 0, 0)
        historico_details_layout.setSpacing(8)
        self._historico_group = historico_card
        historico_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        filtros_layout = QVBoxLayout()
        filtros_layout.setSpacing(8)

        filtros_row_1 = QHBoxLayout()
        filtros_row_1.setSpacing(8)
        self.historico_search_input = QLineEdit()
        self.historico_search_input.setPlaceholderText("Buscar en concepto/notas/columnas…")
        filtros_row_1.addWidget(QLabel("Buscar"))
        filtros_row_1.addWidget(self.historico_search_input, 1)

        self.historico_estado_combo = QComboBox()
        self.historico_estado_combo.addItem("Todos", None)
        for estado in ESTADOS_HISTORICO.values():
            self.historico_estado_combo.addItem(estado.label, estado.code)
        filtros_row_1.addWidget(QLabel("Estado"))
        filtros_row_1.addWidget(self.historico_estado_combo)

        self.historico_delegada_combo = QComboBox()
        self.historico_delegada_combo.addItem("Todas", None)
        filtros_row_1.addWidget(QLabel("Delegada"))
        filtros_row_1.addWidget(self.historico_delegada_combo)
        filtros_layout.addLayout(filtros_row_1)

        filtros_row_2 = QHBoxLayout()
        filtros_row_2.setSpacing(8)
        self.historico_desde_date = QDateEdit()
        self.historico_desde_date.setCalendarPopup(True)
        self.historico_desde_date.setDisplayFormat("yyyy-MM-dd")
        self.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
        filtros_row_2.addWidget(QLabel("Desde"))
        filtros_row_2.addWidget(self.historico_desde_date)

        self.historico_hasta_date = QDateEdit()
        self.historico_hasta_date.setCalendarPopup(True)
        self.historico_hasta_date.setDisplayFormat("yyyy-MM-dd")
        self.historico_hasta_date.setDate(QDate.currentDate())
        filtros_row_2.addWidget(QLabel("Hasta"))
        filtros_row_2.addWidget(self.historico_hasta_date)

        self.historico_last_30_button = QPushButton("Últimos 30 días")
        self.historico_last_30_button.setProperty("variant", "secondary")
        filtros_row_2.addWidget(self.historico_last_30_button)

        self.historico_clear_filters_button = QPushButton("Limpiar filtros")
        self.historico_clear_filters_button.setProperty("variant", "secondary")
        filtros_row_2.addWidget(self.historico_clear_filters_button)
        filtros_row_2.addStretch(1)
        filtros_layout.addLayout(filtros_row_2)
        historico_details_layout.addLayout(filtros_layout)

        self.historico_table = QTableView()
        self.historico_view_model = HistoricalViewModel([])
        self.historico_model = self.historico_view_model.source_model
        self.historico_proxy_model = self.historico_view_model.proxy_model
        self.historico_model.set_show_delegada(True)
        self.historico_table.setModel(self.historico_proxy_model)
        self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.historico_table.selectionModel().selectionChanged.connect(self._on_historico_selection_changed)
        self.historico_table.doubleClicked.connect(self._on_open_historico_detalle)
        self.historico_table.setShowGrid(False)
        self.historico_table.setAlternatingRowColors(True)
        self.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.historico_table.setMinimumHeight(260)
        self._configure_solicitudes_table(self.historico_table)
        self.historico_table.setSortingEnabled(True)
        historico_header = self.historico_table.horizontalHeader()
        historico_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        historico_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        historico_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        historico_header.setSectionResizeMode(5, QHeaderView.Stretch)
        historico_details_layout.addWidget(self.historico_table, 1)

        historico_actions = QHBoxLayout()
        historico_actions.setSpacing(10)
        historico_actions.addStretch(1)
        self.eliminar_button = QPushButton("Eliminar (0)")
        self.eliminar_button.setProperty("variant", "primary")
        self.eliminar_button.setProperty("intent", "destructive")
        self.eliminar_button.clicked.connect(self._on_eliminar)
        historico_actions.addWidget(self.eliminar_button)

        self.ver_detalle_button = QPushButton("Ver detalle (0)")
        self.ver_detalle_button.setProperty("variant", "secondary")
        self.ver_detalle_button.clicked.connect(self._on_open_historico_detalle)
        historico_actions.addWidget(self.ver_detalle_button)

        self.resync_historico_button = QPushButton("Re-sincronizar (0)")
        self.resync_historico_button.setProperty("variant", "secondary")
        self.resync_historico_button.clicked.connect(self._on_resync_historico)
        historico_actions.addWidget(self.resync_historico_button)

        self.generar_pdf_button = QPushButton("Generar PDF (0)")
        self.generar_pdf_button.setProperty("variant", "secondary")
        self.generar_pdf_button.clicked.connect(self._on_generar_pdf_historico)
        historico_actions.addWidget(self.generar_pdf_button)
        historico_details_layout.addLayout(historico_actions)
        historico_layout.addWidget(self.historico_details_content, 1)
        self._configure_disclosure(
            self.historico_details_button,
            self.historico_details_content,
            collapsed_text="Más información",
            expanded_text="Ocultar información",
        )
        historico_tab_layout.addWidget(historico_card, 1)

        self.main_tabs.addTab(historico_tab, "Consulta")

        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(12)
        config_help = QLabel(
            "Gestiona delegada, ajustes del grupo y sincronización desde un único bloque."
        )
        config_help.setWordWrap(True)
        config_help.setProperty("role", "secondary")
        config_layout.addWidget(config_help)

        # UX: Configuración reúne controles avanzados (delegado + ajustes + sync)
        # para que el uso diario no se distraiga con opciones administrativas.
        persona_card, persona_layout = self._create_card("Delegado")

        persona_actions = QHBoxLayout()
        persona_actions.setSpacing(8)
        self.add_persona_button = QPushButton("Nuevo delegado")
        self.add_persona_button.setProperty("variant", "secondary")
        self.add_persona_button.clicked.connect(self._on_add_persona)
        persona_actions.addWidget(self.add_persona_button)

        self.edit_persona_button = QPushButton("Editar delegado")
        self.edit_persona_button.setProperty("variant", "secondary")
        self.edit_persona_button.clicked.connect(self._on_edit_persona)
        persona_actions.addWidget(self.edit_persona_button)
        persona_layout.addLayout(persona_actions)

        persona_selector = QHBoxLayout()
        persona_selector.setSpacing(8)
        persona_label = QLabel("Delegado")
        persona_label.setProperty("role", "sectionTitle")
        persona_selector.addWidget(persona_label)
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        persona_selector.addWidget(self.persona_combo, 1)
        persona_layout.addLayout(persona_selector)

        persona_delete = QHBoxLayout()
        self.delete_persona_button = QPushButton("Eliminar delegado")
        self.delete_persona_button.setProperty("variant", "primary")
        self.delete_persona_button.setProperty("intent", "destructive")
        self.delete_persona_button.clicked.connect(self._on_delete_persona)
        persona_delete.addWidget(self.delete_persona_button)
        persona_delete.addStretch(1)
        persona_layout.addLayout(persona_delete)
        config_layout.addWidget(persona_card)

        ajustes_card, ajustes_layout = self._create_card("Opciones avanzadas")
        ajustes_help = QLabel("Configura grupo, PDF y credenciales de sincronización.")
        ajustes_help.setWordWrap(True)
        ajustes_help.setProperty("role", "secondary")
        ajustes_layout.addWidget(ajustes_help)

        ajustes_actions = QHBoxLayout()
        ajustes_actions.setSpacing(8)
        self.edit_grupo_button = QPushButton("Editar grupo")
        self.edit_grupo_button.setProperty("variant", "secondary")
        self.edit_grupo_button.clicked.connect(self._on_edit_grupo)
        ajustes_actions.addWidget(self.edit_grupo_button)

        self.editar_pdf_button = QPushButton("Opciones (PDF)")
        self.editar_pdf_button.setProperty("variant", "secondary")
        self.editar_pdf_button.clicked.connect(self._on_edit_pdf)
        ajustes_actions.addWidget(self.editar_pdf_button)

        self.opciones_button = QPushButton("Sincronización Google Sheets")
        self.opciones_button.setProperty("variant", "secondary")
        self.opciones_button.clicked.connect(self._on_open_opciones)
        ajustes_actions.addWidget(self.opciones_button)
        ajustes_actions.addStretch(1)
        ajustes_layout.addLayout(ajustes_actions)
        config_layout.addWidget(ajustes_card)

        sync_card, sync_layout = self._create_card("Sincronización")
        sync_heading = QLabel("Google Sheets")
        sync_heading.setProperty("role", "sectionTitle")
        sync_layout.addWidget(sync_heading)
        sync_actions = QHBoxLayout()
        sync_actions.setSpacing(8)
        self.sync_button = QPushButton("Sincronizar ahora")
        self.sync_button.setProperty("variant", "primary")
        self.sync_button.clicked.connect(self._on_sync)
        sync_actions.addWidget(self.sync_button)

        self.simulate_sync_button = QPushButton("Simular sincronización")
        self.simulate_sync_button.setProperty("variant", "secondary")
        self.simulate_sync_button.clicked.connect(self._on_simulate_sync)
        sync_actions.addWidget(self.simulate_sync_button)

        self.confirm_sync_button = QPushButton("Confirmar sincronización")
        self.confirm_sync_button.setProperty("variant", "primary")
        self.confirm_sync_button.setEnabled(False)
        self.confirm_sync_button.clicked.connect(self._on_confirm_sync)
        sync_actions.addWidget(self.confirm_sync_button)

        self.retry_failed_button = QPushButton("Reintentar solo fallidos")
        self.retry_failed_button.setProperty("variant", "secondary")
        self.retry_failed_button.setEnabled(False)
        self.retry_failed_button.clicked.connect(self._on_retry_failed)
        sync_actions.addWidget(self.retry_failed_button)

        self.sync_details_button = QPushButton("Ver detalles")
        self.sync_details_button.setProperty("variant", "secondary")
        self.sync_details_button.setEnabled(False)
        self.sync_details_button.clicked.connect(self._on_show_sync_details)
        sync_actions.addWidget(self.sync_details_button)

        self.copy_sync_report_button = QPushButton("Copiar informe")
        self.copy_sync_report_button.setProperty("variant", "secondary")
        self.copy_sync_report_button.setEnabled(False)
        self.copy_sync_report_button.clicked.connect(self._on_copy_sync_report)
        sync_actions.addWidget(self.copy_sync_report_button)

        self.open_sync_logs_button = QPushButton("Abrir carpeta de logs")
        self.open_sync_logs_button.setProperty("variant", "secondary")
        self.open_sync_logs_button.clicked.connect(self._on_open_sync_logs)
        sync_actions.addWidget(self.open_sync_logs_button)

        self.sync_history_button = QPushButton("Ver historial")
        self.sync_history_button.setProperty("variant", "secondary")
        self.sync_history_button.clicked.connect(self._on_show_sync_history)
        sync_actions.addWidget(self.sync_history_button)

        self.review_conflicts_button = QPushButton("Revisar conflictos")
        self.review_conflicts_button.setProperty("variant", "secondary")
        self.review_conflicts_button.setEnabled(False)
        self.review_conflicts_button.clicked.connect(self._on_review_conflicts)
        sync_actions.addWidget(self.review_conflicts_button)
        sync_layout.addLayout(sync_actions)

        self.last_sync_label = QLabel("Última sync: --")
        self.last_sync_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.last_sync_label)

        self.last_sync_metrics_label = QLabel("Duración: -- · Cambios: -- · Conflictos: -- · Errores: --")
        self.last_sync_metrics_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.last_sync_metrics_label)

        self.sync_trend_label = QLabel("Tendencia (5): --")
        self.sync_trend_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_trend_label)

        sync_state_row = QHBoxLayout()
        sync_state_row.setSpacing(8)
        sync_state_caption = QLabel("Estado actual:")
        sync_state_caption.setProperty("role", "secondary")
        sync_state_row.addWidget(sync_state_caption)
        self.sync_status_badge = QLabel(self._status_to_label("IDLE"))
        self.sync_status_badge.setProperty("role", "badge")
        self.sync_status_badge.setProperty("syncStatus", "IDLE")
        sync_state_row.addWidget(self.sync_status_badge)
        sync_state_row.addStretch(1)
        sync_layout.addLayout(sync_state_row)

        self.sync_panel_status = QLabel("Estado: Pendiente")
        self.sync_panel_status.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_panel_status)

        self.sync_source_label = QLabel("Fuente: --")
        self.sync_source_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_source_label)

        self.sync_scope_label = QLabel("Rango: --")
        self.sync_scope_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_scope_label)

        self.sync_idempotency_label = QLabel("Evita duplicados: --")
        self.sync_idempotency_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_idempotency_label)

        self.sync_counts_label = QLabel("Resumen: creadas 0 · actualizadas 0 · omitidas 0 · conflictos 0 · errores 0")
        self.sync_counts_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.sync_counts_label)

        self.go_to_sync_config_button = QPushButton("Ir a configuración")
        self.go_to_sync_config_button.setProperty("variant", "secondary")
        self.go_to_sync_config_button.setVisible(False)
        self.go_to_sync_config_button.clicked.connect(self._on_open_opciones)
        sync_layout.addWidget(self.go_to_sync_config_button, alignment=Qt.AlignLeft)

        self.sync_status_label = QLabel("Sincronizando con Google Sheets…")
        self.sync_status_label.setProperty("role", "secondary")
        self.sync_status_label.setVisible(False)
        self.sync_progress = QProgressBar()
        self.sync_progress.setRange(0, 0)
        self.sync_progress.setTextVisible(False)
        self.sync_progress.setVisible(False)
        sync_status_row = QHBoxLayout()
        sync_status_row.setSpacing(8)
        sync_status_row.addWidget(self.sync_status_label)
        sync_status_row.addWidget(self.sync_progress, 1)
        sync_layout.addLayout(sync_status_row)

        self.alert_banner_label = QLabel("Alertas: sin alertas activas.")
        self.alert_banner_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.alert_banner_label)

        self.conflicts_reminder_label = QLabel("Hay 0 conflictos pendientes de revisión.")
        self.conflicts_reminder_label.setProperty("role", "secondary")
        self.conflicts_reminder_label.setVisible(False)
        sync_layout.addWidget(self.conflicts_reminder_label)

        health_card, health_layout = self._create_card("Salud del sistema")
        self.health_summary_label = QLabel("Estado general: pendiente de comprobación")
        self.health_summary_label.setProperty("role", "secondary")
        health_layout.addWidget(self.health_summary_label)
        self.health_checks_tree = QTreeWidget()
        self.health_checks_tree.setColumnCount(4)
        self.health_checks_tree.setHeaderLabels(["Estado", "Categoría", "Mensaje", "Acción"])
        self.health_checks_tree.setMinimumHeight(180)
        health_layout.addWidget(self.health_checks_tree)
        health_actions = QHBoxLayout()
        self.refresh_health_button = QPushButton("Actualizar salud")
        self.refresh_health_button.setProperty("variant", "secondary")
        self.refresh_health_button.clicked.connect(self._refresh_health_and_alerts)
        health_actions.addWidget(self.refresh_health_button)
        self.snooze_alerts_button = QPushButton("No mostrar hoy")
        self.snooze_alerts_button.setProperty("variant", "secondary")
        self.snooze_alerts_button.clicked.connect(self._on_snooze_alerts_today)
        health_actions.addWidget(self.snooze_alerts_button)
        health_actions.addStretch(1)
        health_layout.addLayout(health_actions)

        config_layout.addWidget(sync_card)
        config_layout.addWidget(health_card)
        config_layout.addStretch(1)
        self.main_tabs.addTab(config_tab, "Configuración")

        self._scroll_area.setWidget(content)
        self.setCentralWidget(self._scroll_area)
        self._build_status_bar()

        self._normalize_input_heights()
        self._update_responsive_columns()
        self._configure_time_placeholders()
        self._configure_operativa_focus_order()
        self._configure_historico_focus_order()
        self._bind_preventive_validation_events()
        self._historico_search_timer = QTimer(self)
        self._historico_search_timer.setSingleShot(True)
        self._historico_search_timer.setInterval(250)
        self._historico_search_timer.timeout.connect(self._apply_historico_text_filter)
        self.historico_search_input.textChanged.connect(lambda _: self._historico_search_timer.start())
        self.historico_estado_combo.currentIndexChanged.connect(self._apply_historico_filters)
        self.historico_delegada_combo.currentIndexChanged.connect(self._apply_historico_filters)
        self.historico_desde_date.dateChanged.connect(self._apply_historico_filters)
        self.historico_hasta_date.dateChanged.connect(self._apply_historico_filters)
        self.historico_last_30_button.clicked.connect(self._apply_historico_last_30_days)
        self.historico_clear_filters_button.clicked.connect(self._clear_historico_filters)

        self._historico_find_shortcut = QShortcut(QKeySequence.Find, self)
        self._historico_find_shortcut.activated.connect(self._focus_historico_search)
        self._historico_detail_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.historico_table)
        self._historico_detail_shortcut.activated.connect(self._on_open_historico_detalle)
        self._historico_escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._historico_escape_shortcut.activated.connect(self._on_historico_escape)

        self._apply_historico_filters()
        self._update_solicitud_preview()
        self._update_action_state()

    def _build_status_bar(self) -> None:
        status = QStatusBar(self)
        status.setObjectName("mainStatusBar")
        self.setStatusBar(status)
        self.status_sync_label = QLabel("Sincronizando con Google Sheets…")
        self.status_sync_label.setVisible(False)
        self.status_sync_progress = QProgressBar()
        self.status_sync_progress.setRange(0, 0)
        self.status_sync_progress.setTextVisible(False)
        self.status_sync_progress.setVisible(False)
        self.status_pending_label = QLabel("Pendiente: 00:00")
        status.addPermanentWidget(self.status_sync_label)
        status.addPermanentWidget(self.status_sync_progress)
        status.addPermanentWidget(self.status_pending_label)

    def _configure_solicitudes_table(self, table: QTableView) -> None:
        model = table.model()
        column_count = model.columnCount() if model is not None else 6
        if column_count <= 0:
            return
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
        submit_widgets = {
            getattr(self, "persona_combo", None),
            getattr(self, "fecha_input", None),
            getattr(self, "desde_input", None),
            getattr(self, "hasta_input", None),
            getattr(self, "completo_check", None),
            getattr(self, "notas_input", None),
        }
        if watched in submit_widgets and isinstance(event, QKeyEvent):
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.NoModifier:
                if self.primary_cta_button.isEnabled():
                    self.primary_cta_button.click()
                return True
        return super().eventFilter(watched, event)

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
        if not hasattr(self, "_content_row"):
            return
        available_width = self._scroll_area.viewport().width() if hasattr(self, "_scroll_area") else self.width()
        # En ventanas estrechas apilamos columnas para evitar recortes horizontales.
        if available_width < 1200:
            self._content_row.setDirection(QBoxLayout.TopToBottom)
            self._content_row.setStretch(0, 0)
            self._content_row.setStretch(1, 0)
        else:
            self._content_row.setDirection(QBoxLayout.LeftToRight)
            self._content_row.setStretch(0, 3)
            self._content_row.setStretch(1, 2)

    def _build_saldo_field(self) -> QLineEdit:
        field = QLineEdit("00:00")
        field.setReadOnly(True)
        field.setFocusPolicy(Qt.NoFocus)
        field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        field.setProperty("role", "saldo")
        return field

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

    def _on_persona_changed(self) -> None:
        self.pendientes_table.clearSelection()
        self.huerfanas_table.clearSelection()
        self._reload_pending_views()
        self._update_action_state()
        self._refresh_historico()
        self._refresh_saldos()
        self._update_solicitud_preview()

    def _apply_historico_text_filter(self) -> None:
        self.historico_proxy_model.set_search_text(self.historico_search_input.text())
        self._update_action_state()

    def _apply_historico_filters(self) -> None:
        self.historico_proxy_model.set_date_range(self.historico_desde_date.date(), self.historico_hasta_date.date())
        self.historico_proxy_model.set_estado_code(self.historico_estado_combo.currentData())
        self.historico_proxy_model.set_delegada_id(self.historico_delegada_combo.currentData())
        self._apply_historico_text_filter()

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
        self._run_preventive_validation()

    def _run_preventive_validation(self) -> None:
        blocking, warnings = self._collect_preventive_validation()
        self._blocking_errors = blocking
        self._warnings = warnings
        self._render_preventive_validation()

    def _collect_preventive_validation(self) -> tuple[dict[str, str], dict[str, str]]:
        blocking: dict[str, str] = {}
        warnings: dict[str, str] = {}
        self._duplicate_target = None

        persona = self._current_persona()
        if persona is None:
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

        solicitud = self._build_preview_solicitud()
        if solicitud is None or blocking:
            return blocking, warnings

        try:
            minutos = self._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
            year, month, _ = (int(part) for part in solicitud.fecha_pedida.split("-"))
            saldos = self._solicitud_use_cases.calcular_saldos(solicitud.persona_id, year, month)
            if saldos.restantes_mes < minutos or saldos.restantes_ano < minutos:
                blocking["saldo"] = "⚠ Saldo insuficiente para esta solicitud."

            duplicate = self._solicitud_use_cases.buscar_duplicado(solicitud)
            if duplicate is not None:
                blocking["duplicado"] = "⚠ Ya existe una solicitud similar."
                self._duplicate_target = duplicate

            pending_duplicate_row = self._find_pending_duplicate_row(solicitud)
            if pending_duplicate_row is not None:
                blocking["duplicado"] = "⚠ Ya existe una solicitud similar."
                self._duplicate_target = self._pending_solicitudes[pending_duplicate_row]

            conflicto = self._solicitud_use_cases.validar_conflicto_dia(
                solicitud.persona_id, solicitud.fecha_pedida, solicitud.completo
            )
            if not conflicto.ok:
                blocking["conflicto"] = "⚠ Hay un conflicto activo pendiente en esa fecha."

            if solicitud.completo and self.cuadrante_warning_label.isVisible():
                warnings["cuadrante"] = "⚠ El cuadrante no está configurado y puede alterar el cálculo final."
        except (ValidacionError, BusinessRuleError) as exc:
            blocking.setdefault("tramo", f"⚠ {str(exc)}")

        return blocking, warnings

    def _render_preventive_validation(self) -> None:
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
            result = QMessageBox.question(
                self,
                "Advertencias",
                f"Se detectaron advertencias no bloqueantes:\n\n{warning_text}\n\n¿Deseas continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            return result == QMessageBox.StandardButton.Yes
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
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._logs_dir)))

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
            logger.exception("Fallo técnico durante sincronización", exc_info=error)
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
        return SolicitudDTO(
            id=None,
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
        self.agregar_button.setEnabled(persona_selected and form_valid and not has_blocking_errors)
        has_pending = bool(self._pending_solicitudes)
        can_confirm = has_pending and not self._pending_conflict_rows and not self._pending_view_all and not has_blocking_errors
        self.insertar_sin_pdf_button.setEnabled(persona_selected and can_confirm)
        selected_pending = self._selected_pending_solicitudes()
        self.confirmar_button.setEnabled(persona_selected and can_confirm and bool(selected_pending))
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

        form_step_valid = form_valid and not has_blocking_errors
        self.stepper_labels[1].setEnabled(form_step_valid)
        stepper_message = first_blocking_error or form_message or "Completa la solicitud para poder añadirla"
        self.stepper_labels[1].setToolTip("" if form_step_valid else stepper_message)

        active_step = self._resolve_operativa_step(form_step_valid, has_pending, selected_pending, can_confirm)
        self._set_operativa_step(active_step)
        self._update_step_context(active_step)
        self._update_confirmation_summary(selected_pending)

        cta_text = "Confirmar seleccionadas" if selected_pending and can_confirm else "Añadir a pendientes"
        self.primary_cta_button.setText(cta_text)
        if has_blocking_errors:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText(first_blocking_error)
        elif not form_valid:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText(form_message)
        elif selected_pending and can_confirm:
            self.primary_cta_button.setEnabled(True)
            self.primary_cta_hint.setText("")
        elif persona_selected:
            self.primary_cta_button.setEnabled(True)
            self.primary_cta_hint.setText("")
        elif has_pending:
            self.primary_cta_button.setEnabled(False)
            self.primary_cta_hint.setText("Selecciona al menos una pendiente")
        else:
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
            1: "Completa los datos obligatorios",
            2: "Revisa las solicitudes pendientes",
            3: "Confirma para registrar definitivamente",
        }
        self.stepper_context_label.setText(messages.get(active_step, ""))

    def _update_confirmation_summary(self, selected_pending: list[SolicitudDTO]) -> None:
        if not selected_pending:
            self.confirmation_summary_label.clear()
            self.confirmation_summary_label.setVisible(False)
            return

        persona = self._current_persona()
        delegada = persona.nombre if persona is not None else "Sin delegada"
        fechas = sorted({solicitud.fecha_pedida for solicitud in selected_pending})
        fecha_resumen = fechas[0] if len(fechas) == 1 else f"{fechas[0]} +{len(fechas) - 1}"
        total_min = self._sum_solicitudes_minutes(selected_pending)
        self.confirmation_summary_label.setText(
            " · ".join(
                [
                    f"Delegada: {delegada}",
                    f"Fecha: {fecha_resumen}",
                    f"Total horas: {self._format_minutes(total_min)}",
                    f"Solicitudes: {len(selected_pending)}",
                ]
            )
        )
        self.confirmation_summary_label.setVisible(True)

    def _selected_pending_solicitudes(self) -> list[SolicitudDTO]:
        selection_model = self.pendientes_table.selectionModel()
        if selection_model is None:
            return []
        selected_rows = sorted({index.row() for index in selection_model.selectedRows()})
        return [
            self._pending_solicitudes[row]
            for row in selected_rows
            if 0 <= row < len(self._pending_solicitudes)
        ]

    def _on_primary_cta_clicked(self) -> None:
        if self.primary_cta_button.text() == "Confirmar seleccionadas":
            self._on_confirmar()
            return
        self._on_add_pendiente()

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
        persona = self._current_persona()
        if persona is None:
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
        persona = self._current_persona()
        if persona is None:
            return
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
        self._field_touched.update({"delegada", "fecha", "tramo"})
        self._run_preventive_validation()
        if self._blocking_errors:
            self.toast.warning("Corrige los errores pendientes antes de añadir.", title="Validación preventiva")
            return
        self._solicitudes_controller.on_add_pendiente()

    def _find_pending_duplicate_row(self, solicitud: SolicitudDTO) -> int | None:
        for row, pending in enumerate(self._pending_solicitudes):
            if pending.persona_id != solicitud.persona_id:
                continue
            if pending.fecha_pedida != solicitud.fecha_pedida:
                continue
            if pending.completo != solicitud.completo:
                continue
            if pending.desde == solicitud.desde and pending.hasta == solicitud.hasta:
                return row
        return None

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
        if not self._run_preconfirm_checks():
            return
        persona = self._current_persona()
        selected = self._selected_pending_solicitudes()
        if persona is None or not selected:
            return
        if self._pending_conflict_rows:
            self.toast.warning(
                "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                title="Conflictos detectados",
            )
            return

        try:
            self._set_processing_state(True)
            with OperationContext("confirmar_sin_pdf") as operation:
                log_event(logger, "confirmar_sin_pdf_started", {"count": len(selected)}, operation.correlation_id)
                creadas, pendientes_restantes, errores = self._solicitud_use_cases.confirmar_sin_pdf(
                    selected, correlation_id=operation.correlation_id
                )
                log_event(
                    logger,
                    "confirmar_sin_pdf_finished",
                    {"creadas": len(creadas), "errores": len(errores)},
                    operation.correlation_id,
                )
        finally:
            self._set_processing_state(False)
        _ = pendientes_restantes
        self._reload_pending_views()
        self._refresh_historico()
        self._refresh_saldos()
        self._show_confirmation_closure(creadas, errores, operation_name="confirmar_sin_pdf")
        self._notify_historico_filter_if_hidden(creadas)

    def _on_confirmar(self) -> None:
        if not self._run_preconfirm_checks():
            return
        persona = self._current_persona()
        selected = self._selected_pending_solicitudes()
        if persona is None or not selected:
            return
        if self._pending_conflict_rows:
            self.toast.warning(
                "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                title="Conflictos detectados",
            )
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(selected)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF")
            self._show_critical_error(exc)
            return
        default_path = str(Path.home() / default_name)
        pdf_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF",
            default_path,
            "PDF (*.pdf)",
        )
        if not pdf_path:
            return
        correlation_id: str | None = None
        try:
            self._set_processing_state(True)
            with OperationContext("confirmar_y_generar_pdf") as operation:
                correlation_id = operation.correlation_id
                log_event(
                    logger,
                    "confirmar_y_generar_pdf_started",
                    {"count": len(selected), "destino": pdf_path},
                    operation.correlation_id,
                )
                creadas, pendientes_restantes, errores, generado = (
                    self._solicitud_use_cases.confirmar_y_generar_pdf(
                        selected,
                        Path(pdf_path),
                        correlation_id=operation.correlation_id,
                    )
                )
                log_event(
                    logger,
                    "confirmar_y_generar_pdf_finished",
                    {"creadas": len(creadas), "errores": len(errores), "pdf_generado": bool(generado)},
                    operation.correlation_id,
                )
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error confirmando solicitudes")
            self._show_critical_error(exc)
            return
        finally:
            self._set_processing_state(False)
        if generado and self.abrir_pdf_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(generado)))
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
            self.toast.success("Exportación PDF OK")
        _ = pendientes_restantes
        self._reload_pending_views()
        self._refresh_historico()
        self._refresh_saldos()
        self._show_confirmation_closure(creadas, errores, operation_name="confirmar_y_generar_pdf")
        self._notify_historico_filter_if_hidden(creadas)

    def _sum_solicitudes_minutes(self, solicitudes: list[SolicitudDTO]) -> int:
        return sum(int(round(solicitud.horas * 60)) for solicitud in solicitudes)

    def _show_confirmation_closure(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
        *,
        operation_name: str,
    ) -> None:
        payload = self._build_confirmation_payload(creadas, errores)
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
            payload.result_id,
        )
        self.notifications.show_confirmation_closure(payload)

    def _build_confirmation_payload(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
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
            saldo_disponible=self.saldo_periodo_restantes.text(),
            errores=errores,
            status=status,
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            result_id=f"CFM-{datetime.now().strftime('%y%m%d%H%M%S')}",
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
                "Acción recomendada: Comparte la hoja como Editor y reintenta.",
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
        self.status_sync_label.setVisible(in_progress)
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
            logger.exception("Error técnico capturado en UI", exc_info=error)
        message = mapped.as_text()
        self.toast.error(message, title="Error")
        QMessageBox.critical(self, mapped.title, message)

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
        seleccionadas = [sol for sol in self._selected_historico_solicitudes() if sol.id is not None]
        if not seleccionadas:
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
        selection = self.pendientes_table.selectionModel().selectedRows()
        if not selection:
            return
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
        self.saldo_periodo_label.setText("Mensual")

    def _set_saldos_labels(
        self,
        resumen,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
    ) -> None:
        if resumen is None:
            self._set_saldo_line(self.saldo_periodo_consumidas, self.saldo_periodo_restantes, 0, 0)
            self._set_saldo_line(self.saldo_anual_consumidas, self.saldo_anual_restantes, 0, 0)
            self._set_saldo_line(self.saldo_grupo_consumidas, self.saldo_grupo_restantes, 0, 0)
            self._set_bolsa_labels(0, 0, 0)
            self.exceso_badge.setVisible(False)
            return
        consumidas_periodo = resumen.individual.consumidas_periodo_min
        bolsa_periodo = resumen.individual.bolsa_periodo_min
        restantes_periodo = bolsa_periodo - consumidas_periodo

        consumidas_anual = resumen.individual.consumidas_anual_min
        bolsa_anual = resumen.individual.bolsa_anual_min
        restantes_anual = bolsa_anual - consumidas_anual

        consumidas_grupo = resumen.grupo_anual.consumidas_anual_min
        bolsa_grupo = resumen.grupo_anual.bolsa_anual_grupo_min
        restantes_grupo = bolsa_grupo - consumidas_grupo

        self._set_saldo_line(
            self.saldo_periodo_consumidas,
            self.saldo_periodo_restantes,
            consumidas_periodo,
            restantes_periodo,
        )
        self._set_saldo_line(
            self.saldo_anual_consumidas,
            self.saldo_anual_restantes,
            consumidas_anual,
            restantes_anual,
        )
        self._set_saldo_line(
            self.saldo_grupo_consumidas,
            self.saldo_grupo_restantes,
            consumidas_grupo,
            restantes_grupo,
        )
        self._set_bolsa_labels(bolsa_periodo, bolsa_anual, bolsa_grupo)

        exceso = min(restantes_periodo, restantes_anual, restantes_grupo)
        if exceso < 0:
            self.exceso_badge.setText(f"Exceso {self._format_minutes(abs(exceso))}")
            self.exceso_badge.setVisible(True)
        else:
            self.exceso_badge.setVisible(False)

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

    def _set_saldo_line(
        self,
        consumidas_field: QLineEdit,
        restantes_field: QLineEdit,
        consumidas: int,
        restantes: int,
    ) -> None:
        consumidas_field.setText(self._format_minutes(consumidas))
        restantes_text, warning = self._format_restantes(restantes)
        restantes_field.setText(restantes_text)
        self._set_warning_state(restantes_field, warning)

    def _set_warning_state(self, field: QLineEdit, warning: bool) -> None:
        field.setProperty("status", "warning" if warning else None)
        field.style().unpolish(field)
        field.style().polish(field)
        field.update()

    def _set_bolsa_labels(
        self, bolsa_mensual: int, bolsa_delegada: int, bolsa_grupo: int
    ) -> None:
        self.bolsa_mensual_label.setText(self._format_minutes(bolsa_mensual))
        self.bolsa_delegada_label.setText(self._format_minutes(bolsa_delegada))
        self.bolsa_grupo_label.setText(self._format_minutes(bolsa_grupo))

    def _format_restantes(self, minutos: int) -> tuple[str, bool]:
        if minutos < 0:
            return f"Exceso {minutes_to_hhmm(abs(minutos))}", True
        return self._format_minutes(minutos), False

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )

    def _refresh_health_and_alerts(self) -> None:
        if self._health_check_use_case is None:
            self.health_summary_label.setText("Estado general: monitorización no configurada")
            self.alert_banner_label.setText("Alertas: monitorización no disponible.")
            return
        report = self._health_check_use_case.run()
        self._render_health_report(report)
        history = [load_sync_report(path) for path in list_sync_history(Path.cwd())[:5]]
        pending_count = len(list(self._solicitud_use_cases.listar_pendientes_all()))
        alerts = self._alert_engine.evaluate(
            history=history,
            health_report=report,
            pending_count=pending_count,
            silenced_until=self._alert_snooze,
        )
        self._render_alerts(alerts)

    def _render_health_report(self, report: HealthReport) -> None:
        self.health_checks_tree.clear()
        worst = "OK"
        for check in report.checks:
            if check.status == "ERROR":
                worst = "ERROR"
            elif check.status == "WARN" and worst != "ERROR":
                worst = "WARN"
            item = QTreeWidgetItem([check.status, check.category, check.message, "Solucionar"])
            item.setData(0, Qt.UserRole, check.action_id)
            self.health_checks_tree.addTopLevelItem(item)
        self.health_summary_label.setText(f"Estado general: {worst} · actualizado {self._format_timestamp(report.generated_at)}")

    def _render_alerts(self, alerts: list[Alert]) -> None:
        if not alerts:
            self.alert_banner_label.setText("Alertas: sin alertas activas.")
            return
        top = alerts[0]
        self.alert_banner_label.setText(f"Alerta {top.severity}: {top.message} · Acción: {top.action_id}")

    def _on_health_check_action(self, item: QTreeWidgetItem) -> None:
        action_id = item.data(0, Qt.UserRole)
        self._execute_action(action_id)

    def _execute_action(self, action_id: str) -> None:
        if action_id == "open_sync_settings":
            self._on_open_opciones()
            return
        if action_id == "open_sync_panel":
            self.main_tabs.setCurrentIndex(2)
            return
        if action_id == "open_conflicts":
            self._on_review_conflicts()
            return
        if action_id == "open_network_help":
            QMessageBox.information(self, "Conectividad", "Revisa tu conexión de red o VPN y vuelve a intentar.")
            return
        if action_id == "open_db_help":
            QMessageBox.information(self, "Base de datos", "Reinicia la aplicación y ejecuta migraciones si procede.")

    def _on_snooze_alerts_today(self) -> None:
        until = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        for key in ["stale_sync", "high_failure_rate", "repeated_conflicts", "config_incomplete", "pending_local_changes"]:
            self._alert_snooze[key] = until
        self._refresh_health_and_alerts()

    def _refresh_sync_trend_label(self) -> None:
        history = [load_sync_report(path) for path in list_sync_history(Path.cwd())[:5]]
        if not history:
            self.sync_trend_label.setText("Tendencia (5): --")
            return
        chunks = [f"{report.status}:{report.duration_ms}ms" for report in history]
        self.sync_trend_label.setText("Tendencia (5): " + " · ".join(chunks))

    def _refresh_last_sync_label(self) -> None:
        last_sync = self._sync_service.get_last_sync_at()
        if not last_sync:
            self.last_sync_label.setText("Última sync: Nunca")
            return
        formatted = self._format_timestamp(last_sync)
        self.last_sync_label.setText(f"Última sync: {formatted} · Delegada: {self._sync_actor_text()} · Alcance: {self._sync_scope_text()}")

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
