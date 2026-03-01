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
from app.ui.vistas.personas_presenter import resolve_active_delegada_id as resolve_active_delegada_id_presenter
from app.core.observability import OperationContext
from app.bootstrap.logging import log_operational_error

from .layout_builder import HistoricoDetalleDialog, OptionalConfirmDialog, PdfPreviewDialog
logger = logging.getLogger(__name__)
TAB_HISTORICO = 1

def set_processing_state(window, in_progress: bool) -> None:
    window.agregar_button.setEnabled(not in_progress)
    window.confirmar_button.setEnabled(not in_progress)
    window.eliminar_button.setEnabled(not in_progress)
    window.eliminar_pendiente_button.setEnabled(not in_progress)
    if in_progress:
        window.statusBar().showMessage("Procesando…")
    elif not window._sync_in_progress:
        window.statusBar().clearMessage()

def update_action_state(window) -> None:
    if hasattr(window, "_run_preventive_validation"):
        window._run_preventive_validation()
    persona_selected = window._current_persona() is not None
    form_valid, _ = window._validate_solicitud_form()
    presenter_state = build_action_state(
        ActionStateInput(
            persona_selected=persona_selected,
            form_valid=form_valid,
            has_blocking_errors=bool(getattr(window, "_blocking_errors", {})),
            is_editing_pending=window._selected_pending_for_editing() is not None,
            has_pending=bool(window._pending_solicitudes),
            has_pending_conflicts=bool(window._pending_conflict_rows),
            pendientes_count=len(window._iterar_pendientes_en_tabla()),
            selected_historico_count=len(window._selected_historico_solicitudes()),
        )
    )
    window.agregar_button.setEnabled(presenter_state.agregar_enabled)
    window.agregar_button.setText(presenter_state.agregar_text)
    window.insertar_sin_pdf_button.setEnabled(presenter_state.insertar_sin_pdf_enabled)
    window.confirmar_button.setEnabled(debe_habilitar_confirmar_pdf(presenter_state.pendientes_count))
    window.edit_persona_button.setEnabled(presenter_state.edit_persona_enabled)
    window.delete_persona_button.setEnabled(presenter_state.delete_persona_enabled)
    window.edit_grupo_button.setEnabled(presenter_state.edit_grupo_enabled)
    window.editar_pdf_button.setEnabled(presenter_state.editar_pdf_enabled)
    window.eliminar_button.setEnabled(presenter_state.eliminar_enabled)
    window.eliminar_pendiente_button.setEnabled(presenter_state.eliminar_pendiente_enabled)
    window.generar_pdf_button.setEnabled(presenter_state.generar_pdf_enabled)
    window.eliminar_button.setText(presenter_state.eliminar_text)
    window.generar_pdf_button.setText(presenter_state.generar_pdf_text)
    window._sync_historico_select_all_visible_state()
    window._update_solicitudes_status_panel()
    window._dump_estado_pendientes("after_update_action_state")

def resolve_active_delegada_id(delegada_ids: list[int], preferred_id: object) -> int | None:
    return resolve_active_delegada_id_presenter(delegada_ids, preferred_id)

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

    def _limpiar_formulario(self) -> None:
        form_handlers.limpiar_formulario(self)

    def _is_form_dirty(self) -> bool:
        return acciones_personas.is_form_dirty(self)

    def _confirmar_cambio_delegada(self) -> bool:
        return acciones_personas.confirmar_cambio_delegada(self)

    def _save_current_draft(self, persona_id: int | None) -> None:
        return acciones_personas.save_current_draft(self, persona_id)

    def _restore_draft_for_persona(self, persona_id: int | None) -> None:
        return acciones_personas.restore_draft_for_persona(self, persona_id)

    def _update_global_context(self) -> None:
        return

    def _clear_form(self) -> None:
        form_handlers.clear_form(self)

    def _sincronizar_con_confirmacion(self) -> None:
        return acciones_sincronizacion.sincronizar_con_confirmacion(self)

    def _on_sync_with_confirmation(self) -> None:
        return acciones_sincronizacion.on_sync_with_confirmation(self)

    def _on_export_historico_pdf(self) -> None:
        return historico_actions.on_export_historico_pdf(self)

    def _normalize_input_heights(self) -> None:
        return acciones_personas.normalize_input_heights(self)

    def _configure_operativa_focus_order(self) -> None:
        return acciones_personas.configure_operativa_focus_order(self)

    def _apply_help_preferences(self) -> None:
        saved = self._settings.value("ux/mostrar_ayuda", True, type=bool)
        if self.show_help_toggle is not None:
            self.show_help_toggle.setChecked(bool(saved))
            self.show_help_toggle.toggled.connect(self._on_toggle_help)
        self._set_help_visibility(bool(saved))

    def _on_toggle_help(self, checked: bool) -> None:
        self._settings.setValue("ux/mostrar_ayuda", checked)
        self._set_help_visibility(bool(checked))

    def _set_help_visibility(self, visible: bool) -> None:
        for tip in (self.solicitudes_tip_1, self.solicitudes_tip_2, self.solicitudes_tip_3):
            if tip is not None:
                tip.setVisible(visible)
        self._apply_solicitudes_tooltips()

    def _apply_solicitudes_tooltips(self) -> None:
        if self.persona_combo is None:
            return
        extended = bool(self.show_help_toggle is None or self.show_help_toggle.isChecked())
        self.persona_combo.setToolTip(copy_text("solicitudes.tooltip_delegada") if extended else "")
        self.fecha_input.setToolTip(copy_text("solicitudes.tooltip_fecha") if extended else "")
        self.desde_input.setToolTip(copy_text("solicitudes.tooltip_desde") if extended else "")
        self.hasta_input.setToolTip(copy_text("solicitudes.tooltip_hasta") if extended else "")
        self.total_preview_input.setToolTip(copy_text("solicitudes.tooltip_minutos") if extended else "")
        self.notas_input.setToolTip(copy_text("solicitudes.tooltip_notas") if extended else "")

    def _configure_historico_focus_order(self) -> None:
        return historico_actions.configure_historico_focus_order(self)

    def _focus_historico_search(self) -> None:
        self.main_tabs.setCurrentIndex(1)
        return historico_actions.focus_historico_search(self)

    def _update_responsive_columns(self) -> None:
        return acciones_personas.update_responsive_columns(self)

    def _load_personas(self, select_id: int | None = None) -> None:
        return acciones_personas.load_personas(self, select_id=select_id)

    def _current_persona(self) -> PersonaDTO | None:
        return acciones_personas.current_persona(self)

    def _on_persona_changed(self, *_args) -> None:
        return acciones_personas.on_persona_changed(self, *_args)

    def _on_config_delegada_changed(self, *_args) -> None:
        return acciones_personas.on_config_delegada_changed(self, *_args)

    def _restaurar_contexto_guardado(self) -> None:
        return acciones_personas.restaurar_contexto_guardado(self)

    def _selected_config_persona(self) -> PersonaDTO | None:
        return acciones_personas.selected_config_persona(self)

    def _sync_config_persona_actions(self) -> None:
        return acciones_personas.sync_config_persona_actions(self)

    def _apply_historico_text_filter(self) -> None:
        return historico_actions.apply_historico_text_filter(self)

    def _historico_period_filter_state(self) -> tuple[str, int | None, int | None]:
        return historico_actions.historico_period_filter_state(self)

    def _apply_historico_filters(self) -> None:
        historico_actions.apply_historico_filters(self)

    def _update_historico_empty_state(self) -> None:
        return historico_actions.update_historico_empty_state(self)

    def _apply_historico_default_range(self) -> None:
        historico_actions.apply_historico_default_range(self)

    def _apply_historico_last_30_days(self) -> None:
        historico_actions.apply_historico_last_30_days(self)

    def _on_historico_todas_delegadas_toggled(self, checked: bool) -> None:
        self.historico_delegada_combo.setEnabled(not checked)
        if checked:
            self.historico_delegada_combo.setCurrentIndex(0)

    def _on_historico_periodo_mode_changed(self) -> None:
        historico_actions.on_historico_periodo_mode_changed(self)

    def _on_historico_apply_filters(self) -> None:
        historico_actions.on_historico_apply_filters(self)

    def _on_open_saldos_modal(self) -> None:
        logger.info("UI_SALDOS_MODAL_OPEN")
        dialog = QDialog(self)
        dialog.setWindowTitle("Saldos detallados")
        dialog.resize(800, 500)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)

        saldos_widget = SaldosCard(dialog)
        saldos_widget.update_periodo_label(self.saldos_card.saldo_periodo_label.text())
        saldos_widget.saldo_periodo_consumidas.setText(self.saldos_card.saldo_periodo_consumidas.text())
        saldos_widget.saldo_periodo_restantes.setText(self.saldos_card.saldo_periodo_restantes.text())
        saldos_widget.saldo_anual_consumidas.setText(self.saldos_card.saldo_anual_consumidas.text())
        saldos_widget.saldo_anual_restantes.setText(self.saldos_card.saldo_anual_restantes.text())
        saldos_widget.saldo_grupo_consumidas.setText(self.saldos_card.saldo_grupo_consumidas.text())
        saldos_widget.saldo_grupo_restantes.setText(self.saldos_card.saldo_grupo_restantes.text())
        saldos_widget.bolsa_mensual_label.setText(self.saldos_card.bolsa_mensual_label.text())
        saldos_widget.bolsa_delegada_label.setText(self.saldos_card.bolsa_delegada_label.text())
        saldos_widget.bolsa_grupo_label.setText(self.saldos_card.bolsa_grupo_label.text())
        saldos_widget.exceso_badge.setText(self.saldos_card.exceso_badge.text())
        saldos_widget.exceso_badge.setVisible(self.saldos_card.exceso_badge.isVisible())
        saldos_widget.saldos_details_button.setChecked(True)
        layout.addWidget(saldos_widget, 1)

        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "secondary")
        close_button.clicked.connect(dialog.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)
        dialog.exec()

    def _on_historico_escape(self) -> None:
        return historico_actions.on_historico_escape(self)

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
        return validacion_preventiva._bind_preventive_validation_events(self)

    def _mark_field_touched(self, field: str) -> None:
        return validacion_preventiva._mark_field_touched(self, field)

    def _schedule_preventive_validation(self) -> None:
        return validacion_preventiva._schedule_preventive_validation(self)

    def _run_preventive_validation(self) -> None:
        return validacion_preventiva._run_preventive_validation(self)

    def _collect_base_preventive_errors(self) -> dict[str, str]:
        return validacion_preventiva._collect_base_preventive_errors(self)

    def _collect_preventive_business_rules(
        self,
        solicitud: SolicitudDTO,
        warnings: dict[str, str],
        blocking: dict[str, str],
    ) -> None:
        return validacion_preventiva._collect_preventive_business_rules(self, solicitud, warnings, blocking)

    def _collect_pending_duplicates_warning(self, warnings: dict[str, str]) -> None:
        return validacion_preventiva._collect_pending_duplicates_warning(self, warnings)

    def _collect_preventive_validation(self) -> tuple[dict[str, str], dict[str, str]]:
        return validacion_preventiva._collect_preventive_validation(self)

    def _render_preventive_validation(self) -> None:
        return validacion_preventiva._render_preventive_validation(self)

    def _on_go_to_existing_duplicate(self) -> None:
        return validacion_preventiva._on_go_to_existing_duplicate(self)

    def _run_preconfirm_checks(self) -> bool:
        return validacion_preventiva._run_preconfirm_checks(self)

    def _bind_manual_hours_preview_refresh(self) -> None:
        return validacion_preventiva._bind_manual_hours_preview_refresh(self)

    def _sync_completo_visibility(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        self.desde_container.setToolTip(copy_text("solicitudes.no_aplica_completo") if checked else "")
        self.hasta_container.setToolTip(copy_text("solicitudes.no_aplica_completo") if checked else "")

    def _on_edit_grupo(self) -> None:
        dialog = GrupoConfigDialog(self._grupo_use_cases, self._sync_service, self)
        if dialog.exec():
            self._refresh_saldos()

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

    def _on_sync_finished(self, summary: SyncSummary) -> None:
        return acciones_sincronizacion.on_sync_finished(self, summary)

    def _on_sync_simulation_finished(self, plan: SyncExecutionPlan) -> None:
        return acciones_sincronizacion.on_sync_simulation_finished(self, plan)

    def _refresh_after_sync(self, summary: SyncSummary) -> None:
        return acciones_sincronizacion.refresh_after_sync(self, summary)

    def _on_sync_failed(self, payload: object) -> None:
        return acciones_sincronizacion.on_sync_failed(self, payload)

    def _on_review_conflicts(self) -> None:
        return acciones_sincronizacion.on_review_conflicts(self)

    def _on_open_opciones(self) -> None:
        return acciones_sincronizacion.on_open_opciones(self)

    def _open_google_sheets_config(self) -> None:
        return acciones_sincronizacion.open_google_sheets_config(self)

    def _set_config_incomplete_state(self) -> None:
        return acciones_sincronizacion.set_config_incomplete_state(self)

    def _on_edit_pdf(self) -> None:
        dialog = PdfConfigDialog(self._grupo_use_cases, self._sync_service, self)
        dialog.exec()

    def _manual_hours_minutes(self) -> int:
        return validacion_preventiva._manual_hours_minutes(self)

    def _build_preview_solicitud(self) -> SolicitudDTO | None:
        return form_handlers.build_preview_solicitud(self)

    def _calculate_preview_minutes(self) -> tuple[int | None, bool]:
        return validacion_preventiva._calculate_preview_minutes(self)

    def _update_solicitud_preview(self) -> None:
        return validacion_preventiva._update_solicitud_preview(self)

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        return validacion_preventiva._validate_solicitud_form(self)

    def _update_solicitudes_status_panel(self) -> None:
        return validacion_preventiva._update_solicitudes_status_panel(self)

    def _focus_first_invalid_field(self) -> None:
        return validacion_preventiva._focus_first_invalid_field(self)

    def _update_action_state(self) -> None:
        update_action_state(self)

    def _selected_pending_solicitudes(self) -> list[SolicitudDTO]:
        return acciones_pendientes.helper_selected_pending_solicitudes(self)

    def _build_debug_estado_pendientes(self) -> dict[str, object]:
        # Para juniors: lo sacamos a helper para bajar LOC y poder testear diagnóstico sin instanciar la ventana completa.
        return build_estado_pendientes_debug_payload(
            editing_pending=self._selected_pending_for_editing(),
            selected_rows=self._selected_pending_row_indexes(),
            solicitud_form=self._build_preview_solicitud(),
            pending_solicitudes=self._pending_solicitudes,
            agregar_button_text=self.agregar_button.text(),
            agregar_button_enabled=bool(self.agregar_button.isEnabled()),
        )

    def _dump_estado_pendientes(self, motivo: str) -> dict:
        try:
            estado = self._build_debug_estado_pendientes()
        except Exception as exc:  # pragma: no cover - diagnóstico defensivo
            estado = {"motivo": motivo, "error": str(exc)}
            logger.exception("estado_pendientes_failed motivo=%s", motivo)
            return estado
        log_estado_pendientes(motivo, estado)
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
        return acciones_pendientes.helper_refresh_pending_conflicts(self)

    def _refresh_pending_ui_state(self) -> None:
        return acciones_pendientes.helper_refresh_pending_ui_state(self)

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

    def _post_confirm_success(
        self,
        confirmadas_ids: list[int],
        pendientes_restantes: list[SolicitudDTO] | None = None,
    ) -> None:
        if not confirmadas_ids:
            logger.warning("UI_POST_CONFIRM_NO_IDS")
        self._solicitudes_controller.aplicar_confirmacion(confirmadas_ids, pendientes_restantes)
        self._reconstruir_tabla_pendientes()
        self._refrescar_historico()
        self._clear_form()
        self.pendientes_table.clearSelection()
        self._editing_solicitud_id = None
        self._update_global_context()
        logger.info(
            "UI_POST_CONFIRM_OK",
            extra={
                "confirmadas": len(confirmadas_ids),
                "pendientes_restantes": len(self._pending_solicitudes),
                "historico_total": self.historico_model.rowCount() if self.historico_model is not None else None,
            },
        )

    def _procesar_resultado_confirmacion(
        self,
        confirmadas_ids: list[int],
        errores: list[str],
        pendientes_restantes: list[SolicitudDTO] | None = None,
    ) -> None:
        if confirmadas_ids:
            self._post_confirm_success(confirmadas_ids, pendientes_restantes)
            self._refresh_saldos()
            toast_success(self.toast, f"{len(confirmadas_ids)} solicitudes confirmadas", title="Confirmación")
            if errores:
                self.toast.warning(f"{len(errores)} errores", title="Confirmación")
        elif errores:
            self.toast.warning("No se pudo confirmar ninguna solicitud", title="Confirmación")
        logger.info(
            "UI_POST_CONFIRM_REFRESH",
            extra={
                "confirmadas": len(confirmadas_ids),
                "errores": len(errores),
                "pendientes_restantes": len(self._pending_solicitudes),
            },
        )

    def _selected_historico(self) -> SolicitudDTO | None:
        return historico_actions.selected_historico(self)

    def _selected_historico_solicitudes(self) -> list[SolicitudDTO]:
        return historico_actions.selected_historico_solicitudes(self)

    def _on_historico_select_all_visible_toggled(self, checked: bool) -> None:
        return historico_actions.on_historico_select_all_visible_toggled(self, checked)

    def _sync_historico_select_all_visible_state(self) -> None:
        return historico_actions.sync_historico_select_all_visible_state(self)

    def _on_add_persona(self) -> None:
        return acciones_personas.on_add_persona(self)

    def _on_edit_persona(self) -> None:
        return acciones_personas.on_edit_persona(self)

    def _on_delete_persona(self) -> None:
        return acciones_personas.on_delete_persona(self)

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
        return acciones_pendientes.helper_selected_pending_row_indexes(self)

    def _selected_pending_for_editing(self) -> SolicitudDTO | None:
        return acciones_pendientes.helper_selected_pending_for_editing(self)

    def _find_pending_duplicate_row(self, solicitud: SolicitudDTO) -> int | None:
        return acciones_pendientes.helper_find_pending_duplicate_row(self, solicitud)

    def _find_pending_row_by_id(self, solicitud_id: int | None) -> int | None:
        return acciones_pendientes.helper_find_row_by_id(self, solicitud_id)

    def _handle_duplicate_before_add(self, duplicate_row: int) -> bool:
        return acciones_pendientes.on_handle_duplicate_before_add(self, duplicate_row)

    def _focus_pending_row(self, row: int) -> None:
        return acciones_pendientes.helper_focus_pending_row(self, row)

    def _focus_pending_by_id(self, solicitud_id: int | None) -> bool:
        return acciones_pendientes.helper_focus_pending_by_id(self, solicitud_id)

    def _focus_historico_duplicate(self, solicitud: SolicitudDTO) -> None:
        return historico_actions.focus_historico_duplicate(self, solicitud)

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
        return acciones_pendientes.on_resolve_pending_conflict(self, fecha_pedida, completo)

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
        on_insertar_sin_pdf(self)
    def _on_confirmar(self) -> None:
        on_confirmar(self)
    def _iterar_pendientes_en_tabla(self) -> list[dict[str, object]]:
        return iterar_pendientes_en_tabla(self)
    def _prompt_confirm_pdf_path(self, selected: list[SolicitudDTO]) -> str | None:
        return prompt_confirm_pdf_path(self, selected)
    def _execute_confirmar_with_pdf(
        self,
        persona: PersonaDTO,
        selected: list[SolicitudDTO],
        pdf_path: str,
    ) -> tuple[str | None, Path | None, list[SolicitudDTO], list[int], list[str], list[SolicitudDTO] | None] | None:
        return execute_confirmar_with_pdf(self, persona, selected, pdf_path)
    def _finalize_confirmar_with_pdf(
        self,
        persona: PersonaDTO,
        correlation_id: str | None,
        generado: Path | None,
        creadas: list[SolicitudDTO],
        confirmadas_ids: list[int],
        errores: list[str],
        pendientes_restantes: list[SolicitudDTO] | None,
    ) -> None:
        finalize_confirmar_with_pdf(self, persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes)
    def _toast_success(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        toast_success(self.toast, message, title=title)

    def _toast_error(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        toast_error(self.toast, message, title=title)

    def _show_pdf_actions_dialog(self, generated_path: Path) -> None:
        show_pdf_actions_dialog(self, generated_path)
    def _sum_solicitudes_minutes(self, solicitudes: list[SolicitudDTO]) -> int:
        return sum_solicitudes_minutes(solicitudes)
    def _show_confirmation_closure(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
        *,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> None:
        show_confirmation_closure(self, creadas, errores, operation_name=operation_name, correlation_id=correlation_id)
    def _build_confirmation_payload(
        self,
        creadas: list[SolicitudDTO],
        errores: list[str],
        *,
        correlation_id: str | None = None,
    ) -> ConfirmationSummaryPayload:
        return build_confirmation_payload(self, creadas, errores, correlation_id=correlation_id)
    def _undo_confirmation(self, solicitud_ids: list[int]) -> None:
        undo_confirmation(self, solicitud_ids)
    def _ask_push_after_pdf(self) -> None:
        ask_push_after_pdf(self)
    def _on_push_now(self) -> None:
        return acciones_sincronizacion.on_push_now(self)

    def _on_push_finished(self, summary: SyncSummary) -> None:
        return acciones_sincronizacion.on_push_finished(self, summary)

    def _on_push_failed(self, payload: object) -> None:
        return acciones_sincronizacion.on_push_failed(self, payload)

    def _update_sync_button_state(self) -> None:
        return acciones_sincronizacion.update_sync_button_state(self)

    def _update_conflicts_reminder(self) -> None:
        return acciones_sincronizacion.update_conflicts_reminder(self)

    def _show_sync_error_dialog(self, error: Exception, details: str | None) -> None:
        # Para juniors: extraemos mapeo de errores para reducir LOC y volverlo testeable como función aislada.
        return acciones_sincronizacion.show_sync_error_dialog(self, error, details)

    def _apply_sync_report(self, report) -> None:
        return acciones_sincronizacion.apply_sync_report(self, report)

    def _on_show_sync_history(self) -> None:
        return acciones_sincronizacion.on_show_sync_history(self)

    def _show_sync_details_dialog(self) -> None:
        return acciones_sincronizacion.show_sync_details_dialog(self)

    def _set_sync_status_badge(self, status: str) -> None:
        return acciones_sincronizacion.set_sync_status_badge(self, status)

    def _status_from_summary(self, summary: SyncSummary) -> str:
        return acciones_sincronizacion.status_from_summary(summary)

    @staticmethod
    def _status_to_label(status: str) -> str:
        return acciones_sincronizacion.status_to_label(status)

    def _sync_source_text(self) -> str:
        return acciones_sincronizacion.sync_source_text(self)

    def _sync_scope_text(self) -> str:
        return acciones_sincronizacion.sync_scope_text()

    def _sync_actor_text(self) -> str:
        return acciones_sincronizacion.sync_actor_text(self)

    def _show_sync_summary_dialog(self, title: str, summary: SyncSummary) -> None:
        return acciones_sincronizacion.show_sync_summary_dialog(self, title, summary)

    def _normalize_sync_error(self, payload: object) -> tuple[Exception, str | None]:
        return acciones_sincronizacion.normalize_sync_error(payload)

    def _set_sync_in_progress(self, in_progress: bool) -> None:
        return acciones_sincronizacion.set_sync_in_progress(self, in_progress)

    def _set_processing_state(self, in_progress: bool) -> None:
        set_processing_state(self, in_progress)

    def _show_critical_error(self, error: Exception | str) -> None:
        if isinstance(error, str):
            mapped = UiErrorMessage(
                title="Error",
                probable_cause=error,
                recommended_action="Reintentar. Si persiste, contactar con soporte.",
                severity="blocking",
            )
        else:
            mapped = map_error_to_ui_message(error)
            if isinstance(error, BusinessRuleError):
                mapped.title = "Validación"
                mapped.probable_cause = str(error)
                mapped.recommended_action = "Corrige el dato indicado y vuelve a intentarlo."
            logger.exception(
                "Error técnico capturado en UI",
                exc_info=error,
                extra={"correlation_id": mapped.incident_id},
            )
        message = mapped.as_text()
        self._solicitudes_runtime_error = True
        self._update_solicitudes_status_panel()
        self._toast_error(
            message,
            title="Error",
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
        return historico_actions.notify_historico_filter_if_hidden(self, solicitudes_insertadas)

    def _update_pending_totals(self) -> None:
        return acciones_pendientes.helper_update_pending_totals(self)

    def _service_account_email(self) -> str | None:
        return acciones_sincronizacion.service_account_email(self)

    def _on_generar_pdf_historico(self) -> None:
        historico_actions.on_generar_pdf_historico(self)

    def _on_eliminar(self) -> None:
        return historico_actions.on_eliminar(self)

    def _on_remove_pendiente(self) -> None:
        return acciones_pendientes.on_remove_pendiente(self)

    def _refresh_historico(self, *, force: bool = False) -> None:
        data_refresh.refresh_historico(self, force=force)

    def _refresh_saldos(self) -> None:
        data_refresh.refresh_saldos(self)

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
        historico_actions.on_open_historico_detalle(self)

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        periodo_base = self.fecha_input.date() if hasattr(self, "fecha_input") else QDate.currentDate()
        return PeriodoFiltro.mensual(periodo_base.year(), periodo_base.month())

    def _pending_minutes_for_period(self, filtro: PeriodoFiltro) -> int:
        return acciones_pendientes.helper_pending_minutes_for_period(self, filtro)

    def _clear_pendientes(self) -> None:
        return acciones_pendientes.on_clear_pendientes(self)

    def _on_toggle_ver_todas_pendientes(self, checked: bool) -> None:
        self._pending_view_all = checked
        self.persona_combo.setEnabled(not checked)
        self._reload_pending_views()

    def _reload_pending_views(self) -> None:
        data_refresh.reload_pending_views(self)

    def _on_review_hidden_pendientes(self) -> None:
        return acciones_pendientes.on_review_hidden(self)

    def _on_remove_huerfana(self) -> None:
        return acciones_pendientes.on_remove_huerfana(self)

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )
