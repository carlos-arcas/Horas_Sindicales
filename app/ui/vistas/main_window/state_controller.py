from __future__ import annotations

# ruff: noqa: F401

import logging
from pathlib import Path

from app.ui.qt_compat import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDate,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QEvent,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QItemSelectionModel,
    QKeyEvent,
    QLabel,
    QMainWindow,
    QMessageBox,
    QObject,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSettings,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTextEdit,
    QThread,
    QTime,
    QTimeEdit,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)  # noqa: F401

from app.application.conflicts_service import ConflictsService
from app.application.dto import PersonaDTO, SolicitudDTO
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases.conflict_resolution_policy import ConflictResolutionPolicy
from app.application.use_cases.retry_sync_use_case import RetrySyncUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.validacion_preventiva_lock_use_case import ValidacionPreventivaLockUseCase
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan
from app.ui.vistas.main_window.importaciones import (
    ActionStateInput,
    ConfirmationSummaryPayload,
    ConflictsDialog,
    GestorToasts,
    GrupoConfigDialog,
    MainWindowHealthMixin,
    NotificationService,
    OperationFeedback,
    PdfConfigDialog,
    PdfController,
    PersonasController,
    PushWorker,
    STATUS_PATTERNS,
    SaldosCard,
    SolicitudesController,
    SyncController,
    UiErrorMessage,
    abrir_archivo_local,
    acciones_pendientes,
    acciones_personas,
    acciones_sincronizacion,
    apply_modal_behavior,
    ask_push_after_pdf,
    build_action_state,
    build_config_incomplete_report,
    build_confirmation_payload,
    build_estado_pendientes_debug_payload,
    build_failed_report,
    build_historico_filters_payload,
    build_main_window_widgets,
    build_modal_actions,
    build_shell_layout,
    build_simulation_report,
    build_status_bar,
    build_sync_report,
    debe_habilitar_confirmar_pdf,
    execute_confirmar_with_pdf,
    finalize_confirmar_with_pdf,
    handle_historico_render_mismatch,
    historico_actions,
    iterar_pendientes_en_tabla,
    list_sync_history,
    load_sync_report,
    log_estado_pendientes,
    map_error_to_ui_message,
    on_confirmar,
    on_insertar_sin_pdf,
    persist_report,
    prompt_confirm_pdf_path,
    run_init_refresh,
    show_confirmation_closure,
    show_pdf_actions_dialog,
    show_sync_error_dialog_from_exception,
    status_badge,
    sum_solicitudes_minutes,
    to_markdown,
    toast_error,
    toast_success,
    undo_confirmation,
    validacion_preventiva,
)  # noqa: F401

from . import data_refresh, handlers_layout, layout_builder, wiring
from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.qt_hilos import assert_hilo_ui_o_log
from .init_placeholders import inicializar_placeholders

from .layout_builder import HistoricoDetalleDialog, OptionalConfirmDialog, PdfPreviewDialog
from . import state_historico, state_pendientes
from .header_state import resolve_section_title, resolve_sidebar_tab_index

logger = logging.getLogger(__name__)

try:
    from .state_helpers import resolve_active_delegada_id, set_processing_state, update_action_state
except Exception as exc:  # pragma: no cover
    log_operational_error(logger, "MAINWINDOW_STATE_HELPERS_IMPORT_FAILED", exc=exc)

    def set_processing_state(_window, _in_progress: bool) -> None:
        return

    def update_action_state(_window) -> None:
        return

    def resolve_active_delegada_id(_delegada_ids: list[int], _preferred_id: object) -> int | None:
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
        guardar_preferencia_pantalla_completa: GuardarPreferenciaPantallaCompleta | None = None,
        obtener_preferencia_pantalla_completa: ObtenerPreferenciaPantallaCompleta | None = None,
    ) -> None:
        super().__init__()
        assert_hilo_ui_o_log("MainWindow.__init__", logger)
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
        self._guardar_preferencia_pantalla_completa = guardar_preferencia_pantalla_completa
        self._obtener_preferencia_pantalla_completa = obtener_preferencia_pantalla_completa
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
        self._active_sidebar_index = 1
        inicializar_placeholders(self)
        self._last_persona_id: int | None = None
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
        self._inicializar_preferencia_pantalla_completa()
        self._apply_help_preferences()
        self._apply_solicitudes_tooltips()
        self._validate_required_widgets()
        self.toast.attach_to(self)
        self._load_personas()
        self._reload_pending_views()
        self._update_global_context()
        self.sync_source_label.setText(f"{copy_text('ui.sync.fuente_prefix')} {self._sync_source_text()}")
        self.sync_scope_label.setText(f"{copy_text('ui.sync.rango_prefix')} {self._sync_scope_text()}")
        self.sync_idempotency_label.setText(copy_text("ui.sync.idempotencia_regla"))
        if not self._sync_service.is_configured():
            self._set_config_incomplete_state()
        self._refresh_last_sync_label()
        self._update_sync_button_state()
        self._update_conflicts_reminder()
        self._refresh_health_and_alerts()
        self._post_init_load()
        QTimer.singleShot(0, self._warmup_sync_client)


    def _inicializar_preferencia_pantalla_completa(self) -> None:
        if self.preferencia_pantalla_completa_check is None:
            return
        if self._obtener_preferencia_pantalla_completa is None:
            return
        preferencia = self._obtener_preferencia_pantalla_completa.ejecutar()
        self.preferencia_pantalla_completa_check.blockSignals(True)
        self.preferencia_pantalla_completa_check.setChecked(preferencia)
        self.preferencia_pantalla_completa_check.blockSignals(False)

    def _on_toggle_preferencia_pantalla_completa(self, valor: bool) -> None:
        if self._guardar_preferencia_pantalla_completa is None:
            return
        self._guardar_preferencia_pantalla_completa.ejecutar(valor)

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

    def _refresh_historico(self, *, force: bool = False) -> None:
        data_refresh.refresh_historico(self, force=force)

    def _refresh_saldos(self) -> None:
        data_refresh.refresh_saldos(self)

    def _reload_pending_views(self) -> None:
        data_refresh.reload_pending_views(self)

    def _update_action_state(self) -> None:
        update_action_state(self)

    def _update_solicitud_preview(self, *_args: object) -> None:
        self._update_action_state()
        if hasattr(self, "_schedule_preventive_validation"):
            self._schedule_preventive_validation()

    def _on_open_saldos_modal(self) -> None:
        self._refresh_saldos()

    def _on_completo_changed(self, checked: bool) -> None:
        _ = checked
        self._update_solicitud_preview()

    def _on_historico_todas_delegadas_toggled(self, checked: bool) -> None:
        if self.historico_delegada_combo is not None:
            self.historico_delegada_combo.setEnabled(not checked)
        self._apply_historico_filters()

    def _on_add_pendiente(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        if hasattr(acciones_pendientes, "on_add_pendiente"):
            acciones_pendientes.on_add_pendiente(self)
            return
        for nombre in ("_on_agregar", "on_confirmar"):
            handler = getattr(self, nombre, None)
            if callable(handler):
                handler()
                return
        if hasattr(acciones_pendientes, "on_agregar"):
            acciones_pendientes.on_agregar(self)
            return
        if getattr(self, "agregar_button", None) is not None and self.agregar_button.isEnabled():
            self.agregar_button.click()

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
                raise RuntimeError(f"{copy_text('ui.sync.mainwindow_incompleta')} {widget_name}")

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
        collapsed_text: str = copy_text("ui.sync.ver_detalles"),
        expanded_text: str = copy_text("ui.sync.ocultar_detalles"),
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
        target_tab_index = resolve_sidebar_tab_index(index)
        if target_tab_index is None and index != 0:
            return

        self._active_sidebar_index = index

        if self.main_tabs is not None and target_tab_index is not None and self.main_tabs.currentIndex() != target_tab_index:
            self.main_tabs.setCurrentIndex(target_tab_index)

        self._refresh_header_title()

    def _refresh_header_title(self) -> None:
        header_title = getattr(self, "header_title_label", None)
        if header_title is None:
            return

        title = resolve_section_title(self._active_sidebar_index)
        if header_title.text() == title:
            return
        header_title.setText(title)

    def _build_status_bar(self) -> None:
        layout_builder.build_status(self)

    def _configure_time_placeholders(self) -> None:
        handlers_layout.configure_time_placeholders(self)

    def _normalize_input_heights(self) -> None:
        try:
            handlers_layout.normalize_input_heights(self)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_NORMALIZE_INPUT_HEIGHTS_FAILED",
                exc=exc,
                extra={"contexto": "mainwindow._normalize_input_heights"},
            )

    def _update_responsive_columns(self) -> None:
        try:
            handlers_layout.update_responsive_columns(self)
        except Exception as exc:
            log_operational_error(
                logger,
                "UI_UPDATE_RESPONSIVE_COLUMNS_FAILED",
                exc=exc,
                extra={"contexto": "mainwindow._update_responsive_columns"},
            )

    def _configure_operativa_focus_order(self) -> None:
        focus_chain = (
            ("persona_combo", "fecha_input"),
            ("fecha_input", "desde_input"),
            ("desde_input", "hasta_input"),
            ("hasta_input", "completo_check"),
            ("completo_check", "notas_input"),
            ("notas_input", "agregar_button"),
            ("agregar_button", "insertar_sin_pdf_button"),
            ("insertar_sin_pdf_button", "confirmar_button"),
        )
        for before_name, after_name in focus_chain:
            before_widget = getattr(self, before_name, None)
            after_widget = getattr(self, after_name, None)
            if before_widget is None or after_widget is None:
                continue
            self.setTabOrder(before_widget, after_widget)

    def _configure_historico_focus_order(self) -> None:
        """Mantiene compatibilidad con builders aunque falle el binding dinámico."""
        from app.ui.vistas import historico_actions

        historico_actions.configure_historico_focus_order(self)

    def _status_to_label(self, status: str) -> str:
        return handlers_layout.status_to_label(status)

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

    def _save_current_draft(self, persona_id: int | None) -> None:
        return acciones_personas.save_current_draft(self, persona_id)


    def _is_form_dirty(self) -> bool:
        return acciones_personas.is_form_dirty(self)

    def _confirmar_cambio_delegada(self, persona_id: int | None) -> bool:
        return acciones_personas.confirmar_cambio_delegada(self, persona_id)

    def _restore_draft_for_persona(self, persona_id: int | None) -> None:
        return acciones_personas.restore_draft_for_persona(self, persona_id)

    def _load_personas(self) -> None:
        return acciones_personas.load_personas(self)

    def _current_persona(self) -> PersonaDTO | None:
        return acciones_personas.current_persona(self)

    def _on_persona_changed(self) -> None:
        return acciones_personas.on_persona_changed(self)

    def _on_fecha_changed(self, nueva_fecha) -> None:
        _ = nueva_fecha
        update_preview = getattr(self, "_update_solicitud_preview", None)
        if callable(update_preview):
            update_preview()

    def _on_add_persona(self) -> None:
        return acciones_personas.on_add_persona(self)

    def _on_edit_persona(self) -> None:
        return acciones_personas.on_edit_persona(self)

    def _on_delete_persona(self) -> None:
        return acciones_personas.on_delete_persona(self)

    def _sync_config_persona_actions(self) -> None:
        return acciones_personas.sync_config_persona_actions(self)

    def _selected_config_persona(self) -> PersonaDTO | None:
        return acciones_personas.selected_config_persona(self)

    def _on_config_delegada_changed(self) -> None:
        return acciones_personas.on_config_delegada_changed(self)

    def _restaurar_contexto_guardado(self) -> None:
        return acciones_personas.restaurar_contexto_guardado(self)

    def _apply_historico_text_filter(self) -> None:
        return state_historico.aplicar_filtro_texto_historico(self)

    def _apply_historico_default_range(self) -> None:
        """Wrapper: aplica el rango por defecto del histórico."""
        aplicar_ultimo_rango = getattr(self, "_apply_historico_last_30_days", None)
        if callable(aplicar_ultimo_rango):
            aplicar_ultimo_rango()
            return
        state_historico.aplicar_rango_por_defecto_historico(self)

    def _historico_period_filter_state(self) -> tuple[str, int | None, int | None]:
        return state_historico.estado_filtro_periodo_historico(self)

    def _update_historico_empty_state(self) -> None:
        return state_historico.actualizar_estado_vacio_historico(self)

    def _on_historico_escape(self) -> None:
        return state_historico.manejar_escape_historico(self)

    def _selected_historico_solicitudes(self) -> list[SolicitudDTO]:
        return state_historico.obtener_solicitudes_historico_seleccionadas(self)

    def _selected_historico(self) -> SolicitudDTO | None:
        return state_historico.obtener_solicitud_historico_seleccionada(self)

    def _on_historico_select_all_visible_toggled(self, checked: bool) -> None:
        return state_historico.alternar_seleccion_visible_historico(self, checked)

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _on_open_historico_detalle(self) -> None:
        return historico_actions.on_open_historico_detalle(self)

    def _on_generar_pdf_historico(self) -> None:
        return historico_actions.on_generar_pdf_historico(self)

    def _sync_historico_select_all_visible_state(self) -> None:
        return state_historico.sincronizar_estado_seleccion_visible_historico(self)

    def _notify_historico_filter_if_hidden(self, solicitudes_insertadas: list[SolicitudDTO]) -> None:
        return historico_actions.notify_historico_filter_if_hidden(self, solicitudes_insertadas)

    def _on_export_historico_pdf(self) -> None:
        return historico_actions.on_export_historico_pdf(self)

    def _on_eliminar(self) -> None:
        return historico_actions.on_eliminar(self)

    def _bind_preventive_validation_events(self) -> None:
        return validacion_preventiva._bind_preventive_validation_events(self)

    def _mark_field_touched(self, field: str) -> None:
        return validacion_preventiva._mark_field_touched(self, field)

    def _schedule_preventive_validation(self) -> None:
        return validacion_preventiva._schedule_preventive_validation(self)

    def _run_preventive_validation(self) -> None:
        return validacion_preventiva._run_preventive_validation(self)

    def _collect_base_preventive_errors(self) -> dict[str, str]:
        return validacion_preventiva._collect_base_preventive_errors(self)

    def _collect_preventive_validation(self) -> tuple[dict[str, str], dict[str, str]]:
        return validacion_preventiva._collect_preventive_validation(self)

    def _collect_preventive_business_rules(self, errors: dict[str, str], warnings: dict[str, str]) -> None:
        return validacion_preventiva._collect_preventive_business_rules(self, errors, warnings)

    def _collect_pending_duplicates_warning(self, warnings: dict[str, str]) -> None:
        return validacion_preventiva._collect_pending_duplicates_warning(self, warnings)

    def _on_go_to_existing_duplicate(self) -> None:
        return validacion_preventiva._on_go_to_existing_duplicate(self)

    def _on_pending_selection_changed(self) -> None:
        self._update_action_state()

    def _on_toggle_ver_todas_pendientes(self, checked: bool) -> None:
        self._pending_view_all = checked
        self._refresh_pending_ui_state()

    def _on_remove_pendiente(self) -> None:
        return acciones_pendientes.on_remove_pendiente(self)

    def _on_insertar_sin_pdf(self) -> None:
        return on_insertar_sin_pdf(self)

    def _on_confirmar(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        try:
            persona_actual = self._current_persona()
            if persona_actual is None:
                self.toast.warning(
                    copy_text("ui.sync.delegada_no_seleccionada"),
                    title=copy_text("ui.validacion.validacion"),
                )
                return
            confirmar_action = globals().get("on_confirmar")
            if not callable(confirmar_action):
                mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
                detalle = copy_text("ui.errores.reintenta_contacta_soporte")
                toast_error(self.toast, f"{mensaje}. {detalle}")
                log_operational_error(
                    logger,
                    "UI_CONFIRMAR_HANDLER_NO_DISPONIBLE",
                    extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
                )
                return
            confirmar_action(self)
        except Exception as exc:
            mensaje = copy_text("ui.errores.no_se_pudo_completar_operacion")
            detalle = copy_text("ui.errores.reintenta_contacta_soporte")
            toast_error(self.toast, f"{mensaje}. {detalle}")
            log_operational_error(
                logger,
                "UI_CONFIRMAR_HANDLER_FALLO",
                exc=exc,
                extra={"handler": "on_confirmar", "contexto": "mainwindow._on_confirmar"},
            )

    def _render_preventive_validation(self) -> None:
        return validacion_preventiva._render_preventive_validation(self)

    def _run_preconfirm_checks(self) -> bool:
        return validacion_preventiva._run_preconfirm_checks(self)

    def _on_sync(self) -> None:
        return acciones_sincronizacion.on_sync(self)

    def _on_simulate_sync(self) -> None:
        return acciones_sincronizacion.on_simulate_sync(self)

    def _on_confirm_sync(self) -> None:
        return acciones_sincronizacion.on_confirm_sync(self)

    def _on_retry_failed(self) -> None:
        return acciones_sincronizacion.on_retry_failed(self)

    def _on_show_sync_details(self) -> None:
        return acciones_sincronizacion.on_show_sync_details(self)

    def _on_copy_sync_report(self) -> None:
        return acciones_sincronizacion.on_copy_sync_report(self)

    def _on_open_sync_logs(self) -> None:
        return acciones_sincronizacion.on_open_sync_logs(self)

    def _on_show_sync_history(self) -> None:
        return acciones_sincronizacion.on_show_sync_history(self)

    def _on_review_conflicts(self) -> None:
        return acciones_sincronizacion.on_review_conflicts(self)

    def _on_open_opciones(self) -> None:
        return acciones_sincronizacion.on_open_opciones(self)

    def _on_edit_grupo(self) -> None:
        return self._on_open_opciones()

    def _on_edit_pdf(self) -> None:
        return self._on_open_opciones()

    def _on_snooze_alerts_today(self) -> None:
        return MainWindowHealthMixin._on_snooze_alerts_today(self)

    def _on_sync_finished(self, summary) -> None:
        return acciones_sincronizacion.on_sync_finished(self, summary)

    def _on_sync_failed(self, payload: object) -> None:
        return acciones_sincronizacion.on_sync_failed(self, payload)

    def _show_sync_details_dialog(self) -> None:
        return acciones_sincronizacion.show_sync_details_dialog(self)

    def _apply_sync_report(self, report) -> None:
        return acciones_sincronizacion.apply_sync_report(self, report)

    def _selected_pending_row_indexes(self) -> list[int]:
        return state_pendientes.obtener_indices_filas_pendientes_seleccionadas(self)

    def _selected_pending_for_editing(self) -> SolicitudDTO | None:
        return state_pendientes.obtener_pendiente_para_edicion(self)

    def _find_pending_row_by_id(self, solicitud_id: int | None) -> int | None:
        return state_pendientes.buscar_fila_pendiente_por_id(self, solicitud_id)

    def _focus_pending_row(self, row: int) -> None:
        return state_pendientes.enfocar_fila_pendiente(self, row)

    def _focus_pending_by_id(self, solicitud_id: int | None) -> bool:
        return state_pendientes.enfocar_pendiente_por_id(self, solicitud_id)

    def _update_pending_totals(self) -> None:
        return acciones_pendientes.helper_update_pending_totals(self)

    def _refresh_pending_conflicts(self) -> None:
        return acciones_pendientes.helper_refresh_pending_conflicts(self)

    def _refresh_pending_ui_state(self) -> None:
        return acciones_pendientes.helper_refresh_pending_ui_state(self)

    def _clear_pendientes(self) -> None:
        return acciones_pendientes.on_clear_pendientes(self)

    def _on_review_hidden_pendientes(self) -> None:
        return acciones_pendientes.on_review_hidden(self)

    def _on_remove_huerfana(self) -> None:
        return acciones_pendientes.on_remove_huerfana(self)

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
