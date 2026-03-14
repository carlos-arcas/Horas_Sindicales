from __future__ import annotations

from app.ui.copy_catalog import copy_text

try:
    from app.ui.conflicts_dialog import ConflictsDialog
    from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
    from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
    from app.ui.patterns import apply_modal_behavior, build_modal_actions, status_badge, STATUS_PATTERNS
    from app.ui.widgets.toast import GestorToasts
    from app.ui.controllers.personas_controller import PersonasController
    from app.ui.controllers.solicitudes_controller import SolicitudesController
    from app.ui.controllers.sync_controller import SyncController
    from app.ui.controllers.pdf_controller import PdfController
    from app.ui.notification_service import ConfirmationSummaryPayload, NotificationService, OperationFeedback
    from app.ui.toast_helpers import toast_error, toast_success
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
    from app.ui.workers.sincronizacion_workers import PushWorker
    from app.ui.vistas.main_window_health_mixin import MainWindowHealthMixin
    from app.ui.vistas.init_refresh import run_init_refresh
    from app.ui.vistas.builders.main_window_builders import build_main_window_widgets, build_shell_layout, build_status_bar
    from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf
    from app.ui.vistas.confirmacion_actions import (
        ask_push_after_pdf,
        build_confirmation_payload,
        execute_confirmar_with_pdf,
        finalize_confirmar_with_pdf,
        iterar_pendientes_en_tabla,
        on_confirmar,
        on_insertar_sin_pdf,
        prompt_confirm_pdf_path,
        show_confirmation_closure,
        show_pdf_actions_dialog,
        sum_solicitudes_minutes,
        undo_confirmation,
    )
    from app.ui.vistas import historico_actions
    from app.ui.vistas.ui_helpers import abrir_archivo_local
    from app.ui.vistas.main_window_helpers import (
        build_estado_pendientes_debug_payload,
        build_historico_filters_payload,
        handle_historico_render_mismatch,
        log_estado_pendientes,
        show_sync_error_dialog_from_exception,
    )
    import app.ui.vistas.main_window.acciones_pendientes as acciones_pendientes
    import app.ui.vistas.main_window.acciones_personas as acciones_personas
    import app.ui.vistas.main_window.acciones_sincronizacion as acciones_sincronizacion
    import app.ui.vistas.main_window.validacion_preventiva as validacion_preventiva
    from app.ui.vistas.solicitudes_presenter import ActionStateInput, build_action_state
except ImportError:  # pragma: no cover - habilita import parcial sin dependencias de UI/Qt
    def _qt_unavailable(*args, **kwargs):
        raise RuntimeError(copy_text("ui.sync.qt_no_disponible"))

    ConflictsDialog = GrupoConfigDialog = PdfConfigDialog = GestorToasts = object
    ActionStateInput = object
    build_action_state = _qt_unavailable
    acciones_pendientes = acciones_personas = acciones_sincronizacion = validacion_preventiva = object
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
