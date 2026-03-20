from __future__ import annotations

# ruff: noqa: F401

import importlib
import logging
from pathlib import Path

from app.ui.qt_compat import (
    QLabel,
    QDate,
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
from app.application.use_cases.confirmacion_pdf.coordinador_confirmacion_pdf import (
    CoordinadorConfirmacionPdf,
)
from app.application.use_cases.confirmacion_pdf.servicio_destino_pdf_confirmacion import (
    ServicioDestinoPdfConfirmacion,
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
from app.ui.dialogos.dialogo_saldos_detalle import SaldosDetalleDialog
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
from aplicacion.casos_de_uso.preferencia_inicio_maximizado import (
    GuardarPreferenciaInicioMaximizado,
    ObtenerPreferenciaInicioMaximizado,
)
from aplicacion.puertos.proveedor_i18n import ProveedorI18N
from app.application.modo_solo_lectura import EstadoModoSoloLectura

from .capacidades_opcionales import (
    CAPACIDAD_MODAL_SALDOS_DETALLE,
    capacidad_disponible,
    registrar_capacidades_opcionales,
)
from .acciones_mixin import AccionesMainWindowMixin
from .estado_mixin import EstadoMainWindowMixin
from .inicializacion_mixin import InicializacionMainWindowMixin
from .layout_builder import (
    HistoricoDetalleDialog,
    OptionalConfirmDialog,
    PdfPreviewDialog,
)
from .navegacion_mixin import NavegacionMainWindowMixin, TAB_HISTORICO
from .refresco_mixin import RefrescoMainWindowMixin
from .init_placeholders import inicializar_placeholders

logger = logging.getLogger(__name__)


def _importar_componente_critico(
    modulo: str, simbolos: tuple[str, ...]
) -> tuple[object, ...]:
    try:
        modulo_cargado = importlib.import_module(modulo, package=__package__)
        return tuple(getattr(modulo_cargado, simbolo) for simbolo in simbolos)
    except Exception as exc:  # pragma: no cover
        log_operational_error(
            logger,
            "MAINWINDOW_CRITICAL_UI_IMPORT_FAILED",
            exc=exc,
            extra={"modulo": modulo, "simbolos": list(simbolos)},
        )
        raise RuntimeError(
            f"No se pudo importar el módulo crítico de MainWindow {modulo}: {exc}"
        ) from exc


(resolve_active_delegada_id, set_processing_state, update_action_state) = (
    _importar_componente_critico(
        ".state_helpers",
        ("resolve_active_delegada_id", "set_processing_state", "update_action_state"),
    )
)
(MainWindowStateActionsMixin,) = _importar_componente_critico(
    ".state_actions", ("MainWindowStateActionsMixin",)
)
(MainWindowStateValidationMixin,) = _importar_componente_critico(
    ".state_validations", ("MainWindowStateValidationMixin",)
)
(registrar_state_bindings,) = _importar_componente_critico(
    ".state_bindings", ("registrar_state_bindings",)
)


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
        coordinador_confirmacion_pdf: CoordinadorConfirmacionPdf | None = None,
        servicio_destino_pdf_confirmacion: ServicioDestinoPdfConfirmacion | None = None,
        crear_pendiente_caso_uso: CrearPendienteCasoUso | None = None,
        guardar_preferencia_inicio_maximizado: GuardarPreferenciaInicioMaximizado
        | None = None,
        obtener_preferencia_inicio_maximizado: ObtenerPreferenciaInicioMaximizado
        | None = None,
        servicio_i18n: ProveedorI18N | None = None,
        estado_modo_solo_lectura: EstadoModoSoloLectura | None = None,
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
        self._coordinador_confirmacion_pdf = coordinador_confirmacion_pdf
        self._servicio_destino_pdf_confirmacion = servicio_destino_pdf_confirmacion
        self._crear_pendiente_caso_uso = crear_pendiente_caso_uso
        self._alert_snooze: dict[str, str] = {}
        self._guardar_preferencia_inicio_maximizado = (
            guardar_preferencia_inicio_maximizado
        )
        self._obtener_preferencia_inicio_maximizado = (
            obtener_preferencia_inicio_maximizado
        )
        self._settings = QSettings("HorasSindicales", "HorasSindicales")
        self._servicio_i18n = servicio_i18n
        if estado_modo_solo_lectura is None:
            raise TypeError(copy_text("ui.read_only.error_estado_obligatorio"))
        if not isinstance(estado_modo_solo_lectura, EstadoModoSoloLectura):
            raise TypeError(copy_text("ui.read_only.error_estado_invalido"))
        self._estado_modo_solo_lectura = estado_modo_solo_lectura
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
        self._pending_otras_delegadas: list[SolicitudDTO] = []
        self._historico_ids_seleccionados: set[int] = set()
        self._pending_conflict_rows: set[int] = set()
        self._pending_view_all = False
        self._pending_selection_anchor_row: int | None = None
        self._pending_bulk_selection_in_progress = False
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
        registrar_capacidades_opcionales(
            self,
            {CAPACIDAD_MODAL_SALDOS_DETALLE: SaldosDetalleDialog},
        )

        self.setWindowTitle(copy_text("ui.sync.window_title"))
        self._build_ui()
        self.stack = self.stacked_pages or self.centralWidget() or self.main_tabs
        registrar_refresco_idioma(self._refrescar_textos_sync)
        self._refrescar_textos_sync()
        self._inicializar_preferencia_inicio_maximizado()
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

    def tiene_capacidad_opcional(self, nombre_capacidad: str) -> bool:
        return capacidad_disponible(self, nombre_capacidad)

    def _on_config_delegada_changed(self, *_args: object) -> None:
        return super()._on_config_delegada_changed(*_args)

    def _bind_preventive_validation_events(self) -> None:
        return super()._bind_preventive_validation_events()

    def _mark_field_touched(self, field_name: str) -> None:
        return super()._mark_field_touched(field_name)

    def _schedule_preventive_validation(self, debounce_ms: int | None = None) -> None:
        return super()._schedule_preventive_validation(debounce_ms)

    def _run_preventive_validation(self) -> None:
        return super()._run_preventive_validation()

    def _collect_base_preventive_errors(self) -> list[str]:
        return super()._collect_base_preventive_errors()

    def _collect_preventive_validation(
        self,
    ) -> tuple[dict[str, str], dict[str, str], list[SolicitudDTO], object]:
        return super()._collect_preventive_validation()

    def _collect_preventive_business_rules(
        self,
    ) -> tuple[dict[str, str], dict[str, str]]:
        return super()._collect_preventive_business_rules()

    def _collect_pending_duplicates_warning(
        self,
    ) -> tuple[str | None, list[SolicitudDTO]]:
        return super()._collect_pending_duplicates_warning()

    def _on_go_to_existing_duplicate(self) -> None:
        return super()._on_go_to_existing_duplicate()

    # fmt: off
    def _render_preventive_validation(self, blocking: dict[str, str], warnings: dict[str, str], duplicate_target: SolicitudDTO | None) -> None:
        return super()._render_preventive_validation(blocking, warnings, duplicate_target)
    # fmt: on

    def _run_preconfirm_checks(self) -> bool:
        return super()._run_preconfirm_checks()

    def _on_fecha_changed(self, qdate: QDate) -> None:
        self._fecha_seleccionada = qdate
        self._update_solicitud_preview()
        return super()._on_fecha_changed(qdate)

    def _on_add_pendiente(self, *args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        return super()._on_add_pendiente(*args, **kwargs)

    def _on_confirmar(self, *args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        return super()._on_confirmar(*args, **kwargs)

    def _update_solicitud_preview(self, *args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        return super()._update_solicitud_preview()

    def _apply_historico_default_range(self) -> None:
        return super()._apply_historico_default_range()

    def _status_to_label(self, status: str) -> str:
        return super()._status_to_label(status)

    def _normalize_input_heights(self) -> None:
        return super()._normalize_input_heights()

    def _update_responsive_columns(self) -> None:
        return super()._update_responsive_columns()

    def _configure_time_placeholders(self) -> None:
        return super()._configure_time_placeholders()

    def _configure_operativa_focus_order(self) -> None:
        return super()._configure_operativa_focus_order()

    def _configure_historico_focus_order(self) -> None:
        return super()._configure_historico_focus_order()

    def _on_historico_selection_changed(self, *_args: object) -> None:
        return super()._on_historico_selection_changed(*_args)

    def _on_open_historico_detalle(self) -> None:
        return super()._on_open_historico_detalle()

    def _on_generar_pdf_historico(self) -> None:
        return super()._on_generar_pdf_historico()

    def _on_open_saldos_modal(self) -> None:
        return super()._on_open_saldos_modal()

    def _on_main_tab_changed(self, index: int) -> None:
        return super()._on_main_tab_changed(index)


registrar_state_bindings(MainWindow)
