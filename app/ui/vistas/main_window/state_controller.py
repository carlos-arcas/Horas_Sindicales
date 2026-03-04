from __future__ import annotations

# ruff: noqa: F401

import logging
from pathlib import Path

from app.ui.qt_compat import (
    QLabel,
    QMainWindow,
    QProgressBar,
    QSettings,
    QSplitter,
    QThread,
    QTimer,
    QPushButton,
    QWidget,
)

from app.application.conflicts_service import ConflictsService
from app.application.dto import PersonaDTO, SolicitudDTO
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases import (
    GrupoConfigUseCases,
    PersonaUseCases,
    SolicitudUseCases,
)
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.confirmacion_pdf.caso_uso import (
    ConfirmarPendientesPdfCasoUso,
)
from app.application.use_cases.conflict_resolution_policy import (
    ConflictResolutionPolicy,
)
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.retry_sync_use_case import RetrySyncUseCase
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    CrearPendienteCasoUso,
)
from app.application.use_cases.validacion_preventiva_lock_use_case import (
    ValidacionPreventivaLockUseCase,
)
from app.bootstrap.logging import log_operational_error
from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan
from app.ui.copy_catalog import copy_text
from app.ui.i18n_interfaz import configurar_i18n_interfaz, registrar_refresco_idioma
from app.ui.qt_hilos import assert_hilo_ui_o_log
from app.ui.vistas.main_window.importaciones import (
    GestorToasts,
    MainWindowHealthMixin,
    NotificationService,
    PdfController,
    PersonasController,
    PushWorker,
    SaldosCard,
    SolicitudesController,
    SyncController,
)
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from aplicacion.puertos.proveedor_i18n import ProveedorI18N

from .acciones_mixin import AccionesMainWindowMixin
from .estado_mixin import EstadoMainWindowMixin
from .inicializacion_mixin import InicializacionMainWindowMixin
from .layout_builder import (
    HistoricoDetalleDialog,
    OptionalConfirmDialog,
    PdfPreviewDialog,
)
from .navegacion_mixin import NavegacionMainWindowMixin
from .refresco_mixin import RefrescoMainWindowMixin
from .init_placeholders import inicializar_placeholders

logger = logging.getLogger(__name__)

try:
    from .state_helpers import (
        resolve_active_delegada_id,
        set_processing_state,
        update_action_state,
    )
except Exception as exc:  # pragma: no cover
    log_operational_error(logger, "MAINWINDOW_STATE_HELPERS_IMPORT_FAILED", exc=exc)

    def set_processing_state(_window, _in_progress: bool) -> None:
        return

    def update_action_state(_window) -> None:
        return

    def resolve_active_delegada_id(
        _delegada_ids: list[int], _preferred_id: object
    ) -> int | None:
        return None


try:
    from .state_actions import MainWindowStateActionsMixin
except Exception as exc:  # pragma: no cover
    log_operational_error(logger, "MAINWINDOW_STATE_ACTIONS_IMPORT_FAILED", exc=exc)

    class MainWindowStateActionsMixin:
        pass


try:
    from .state_validations import MainWindowStateValidationMixin
except Exception as exc:  # pragma: no cover
    log_operational_error(logger, "MAINWINDOW_STATE_VALIDATIONS_IMPORT_FAILED", exc=exc)

    class MainWindowStateValidationMixin:
        pass


try:
    from .state_bindings import registrar_state_bindings
except Exception as exc:  # pragma: no cover
    log_operational_error(logger, "MAINWINDOW_STATE_BINDINGS_IMPORT_FAILED", exc=exc)

    def registrar_state_bindings(_cls) -> None:
        return


class MainWindow(
    QMainWindow,
    NavegacionMainWindowMixin,
    RefrescoMainWindowMixin,
    AccionesMainWindowMixin,
    EstadoMainWindowMixin,
    InicializacionMainWindowMixin,
    MainWindowStateActionsMixin,
    MainWindowStateValidationMixin,
    MainWindowHealthMixin,
):
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
        validacion_preventiva_lock_use_case: ValidacionPreventivaLockUseCase
        | None = None,
        confirmar_pendientes_pdf_caso_uso: ConfirmarPendientesPdfCasoUso | None = None,
        crear_pendiente_caso_uso: CrearPendienteCasoUso | None = None,
        guardar_preferencia_pantalla_completa: GuardarPreferenciaPantallaCompleta
        | None = None,
        obtener_preferencia_pantalla_completa: ObtenerPreferenciaPantallaCompleta
        | None = None,
        servicio_i18n: ProveedorI18N | None = None,
    ) -> None:
        super().__init__()
        assert_hilo_ui_o_log("ui.mainwindow.init", logger)
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
        self._confirmar_pendientes_pdf_caso_uso = confirmar_pendientes_pdf_caso_uso
        self._crear_pendiente_caso_uso = crear_pendiente_caso_uso
        self._alert_snooze: dict[str, str] = {}
        self._guardar_preferencia_pantalla_completa = (
            guardar_preferencia_pantalla_completa
        )
        self._obtener_preferencia_pantalla_completa = (
            obtener_preferencia_pantalla_completa
        )
        self._settings = QSettings("HorasSindicales", "HorasSindicales")
        self._servicio_i18n = servicio_i18n
        if servicio_i18n is not None:
            try:
                i18n_actual = self._i18n
            except AttributeError:
                self._i18n = servicio_i18n
            else:
                if i18n_actual is None:
                    self._i18n = servicio_i18n
            configurar_i18n_interfaz(servicio_i18n)

        self._personas: list[PersonaDTO] = []
        self._pending_solicitudes: list[SolicitudDTO] = []
        self._pending_all_solicitudes: list[SolicitudDTO] = []
        self._hidden_pendientes: list[SolicitudDTO] = []
        self._historico_ids_seleccionados: set[int] = set()
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
        self._preventive_validation_timer.timeout.connect(
            self._run_preventive_validation
        )
        self._ui_ready = False
        self._solicitudes_runtime_error = False
        self._solicitudes_last_action_saved = False
        self._help_toggle_conectado = False
        self.status_sync_label: QLabel | None = None
        self.status_sync_progress: QProgressBar | None = None
        self.status_pending_label: QLabel | None = None
        self.saldos_card: SaldosCard | None = None
        self.horas_input: object | None = None
        self.sidebar = None
        self.stack: QWidget | None = None
        self.stacked_pages: QWidget | None = None
        self.page_historico: QWidget | None = None
        self.page_configuracion: QWidget | None = None
        self.page_sincronizacion: QWidget | None = None
        self.page_solicitudes: QWidget | None = None
        self.solicitudes_splitter: QSplitter | None = None
        self.sidebar_buttons: list[QPushButton] = []
        self._sidebar_routes: list[dict[str, int | None]] = []
        self._active_sidebar_index = 1
        inicializar_placeholders(self)
        self._last_persona_id: int | None = None
        self._fecha_seleccionada = None
        self._draft_solicitud_por_persona: dict[int, dict[str, object]] = {}

        self.toast = GestorToasts()
        self.notifications = NotificationService(self.toast, self)
        self._personas_controller = PersonasController(self)
        self._solicitudes_controller = SolicitudesController(self)
        self._sync_controller = SyncController(self)
        self._pdf_controller = PdfController(self._solicitud_use_cases)
        self._pdf_preview_dialog_class = PdfPreviewDialog
        self._historico_detalle_dialog_class = HistoricoDetalleDialog
        self._optional_confirm_dialog_class = OptionalConfirmDialog

        self.setWindowTitle(copy_text("ui.sync.window_title"))
        self._build_ui()
        self.stack = self.stacked_pages or self.centralWidget() or self.main_tabs
        registrar_refresco_idioma(self._refrescar_textos_sync)
        self._refrescar_textos_sync()
        self._inicializar_preferencia_pantalla_completa()
        self._apply_help_preferences()
        self._apply_solicitudes_tooltips()
        self._validate_required_widgets()
        self.toast.attach_to(self)
        self._load_personas()
        self._reload_pending_views()
        self._update_global_context()
        self.sync_source_label.setText(
            f"{copy_text('ui.sync.fuente_prefix')} {self._sync_source_text()}"
        )
        self.sync_scope_label.setText(
            f"{copy_text('ui.sync.rango_prefix')} {self._sync_scope_text()}"
        )
        self.sync_idempotency_label.setText(copy_text("ui.sync.idempotencia_regla"))
        if not self._sync_service.is_configured():
            self._set_config_incomplete_state()
        self._refresh_last_sync_label()
        self._sync_controller.update_sync_button_state()
        self._update_conflicts_reminder()
        self._refresh_health_and_alerts()
        self._post_init_ui()


registrar_state_bindings(MainWindow)
