from __future__ import annotations

from collections.abc import Callable
import logging
from types import SimpleNamespace
from typing import Any

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text

logger = logging.getLogger(__name__)


class ImportacionCriticaMainWindowError(RuntimeError):
    """Señala que una dependencia crítica de MainWindow no pudo cargarse."""


def _qt_unavailable(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError(copy_text("ui.sync.qt_no_disponible"))


class _HistoricoActionsFallback:
    def __getattr__(self, _name: str) -> Callable[..., None]:
        return _qt_unavailable


class _NamespaceImportaciones(SimpleNamespace):
    def como_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def _es_import_error_qt_esperado(error: ImportError) -> bool:
    nombre_modulo = getattr(error, "name", "") or ""
    mensaje = str(error)
    pistas_qt = (
        "PySide6",
        "shiboken6",
        "Qt",
    )
    return nombre_modulo.startswith(("PySide6", "shiboken6", "Qt")) or any(
        pista in mensaje for pista in pistas_qt
    )


SIMBOLOS_CRITICOS_POR_GRUPO: dict[str, tuple[str, ...]] = {
    "dialogos": (
        "ConflictsDialog",
        "GrupoConfigDialog",
        "PdfConfigDialog",
        "UiErrorMessage",
        "map_error_to_ui_message",
        "GestorToasts",
        "PersonasController",
        "SolicitudesController",
        "SyncController",
        "PdfController",
        "ConfirmationSummaryPayload",
        "NotificationService",
        "OperationFeedback",
    ),
    "helpers": (
        "SaldosCard",
        "PushWorker",
        "MainWindowHealthMixin",
        "apply_modal_behavior",
        "build_modal_actions",
        "status_badge",
        "build_config_incomplete_report",
        "build_failed_report",
        "build_simulation_report",
        "build_sync_report",
        "list_sync_history",
        "load_sync_report",
        "persist_report",
        "to_markdown",
        "run_init_refresh",
        "build_main_window_widgets",
        "build_shell_layout",
        "build_status_bar",
        "abrir_archivo_local",
        "build_estado_pendientes_debug_payload",
        "build_historico_filters_payload",
        "handle_historico_render_mismatch",
        "log_estado_pendientes",
        "show_sync_error_dialog_from_exception",
    ),
}


def _elevar_importacion_critica(
    *,
    nombre_grupo: str,
    error: ImportError,
    simbolos_criticos: tuple[str, ...],
) -> None:
    payload_extra = {
        "grupo": nombre_grupo,
        "simbolos_criticos": list(simbolos_criticos),
        "error": str(error),
        "modulo": getattr(error, "name", "") or None,
    }
    log_operational_error(
        logger,
        "MAINWINDOW_UI_CRITICAL_IMPORT_FAILED",
        exc=error,
        extra=payload_extra,
    )
    simbolos = ", ".join(simbolos_criticos)
    raise ImportacionCriticaMainWindowError(
        "No se pudieron importar dependencias críticas de MainWindow "
        f"para el grupo '{nombre_grupo}': {simbolos}. "
        "Verifica la instalación de Qt/PySide6 o usa stubs explícitos en tests headless. "
        f"ImportError original: {error}"
    ) from error


def _cargar_importacion_grupo(
    cargar: Callable[[], dict[str, Any]],
    fallback: dict[str, Any],
    *,
    nombre_grupo: str = "desconocido",
    simbolos_criticos: tuple[str, ...] = (),
) -> dict[str, Any]:
    try:
        return cargar()
    except ImportError as error:
        if not _es_import_error_qt_esperado(error):
            raise
        if simbolos_criticos:
            _elevar_importacion_critica(
                nombre_grupo=nombre_grupo,
                error=error,
                simbolos_criticos=simbolos_criticos,
            )
        return fallback


def _resolver_namespace_importaciones(
    cargar: Callable[[], dict[str, Any]],
    fallback: dict[str, Any],
    *,
    nombre_grupo: str,
    simbolos_criticos: tuple[str, ...] = (),
) -> _NamespaceImportaciones:
    simbolos = _cargar_importacion_grupo(
        cargar,
        fallback,
        nombre_grupo=nombre_grupo,
        simbolos_criticos=simbolos_criticos,
    )
    return _NamespaceImportaciones(**simbolos)


def _cargar_grupo_dialogos_y_controllers() -> dict[str, Any]:
    from app.ui.conflicts_dialog import ConflictsDialog
    from app.ui.controllers.pdf_controller import PdfController
    from app.ui.controllers.personas_controller import PersonasController
    from app.ui.controllers.solicitudes_controller import SolicitudesController
    from app.ui.controllers.sync_controller import SyncController
    from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
    from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
    from app.ui.notification_service import (
        ConfirmationSummaryPayload,
        NotificationService,
        OperationFeedback,
    )
    from app.ui.widgets.toast import GestorToasts

    return {
        "ConflictsDialog": ConflictsDialog,
        "GrupoConfigDialog": GrupoConfigDialog,
        "PdfConfigDialog": PdfConfigDialog,
        "UiErrorMessage": UiErrorMessage,
        "map_error_to_ui_message": map_error_to_ui_message,
        "GestorToasts": GestorToasts,
        "PersonasController": PersonasController,
        "SolicitudesController": SolicitudesController,
        "SyncController": SyncController,
        "PdfController": PdfController,
        "ConfirmationSummaryPayload": ConfirmationSummaryPayload,
        "NotificationService": NotificationService,
        "OperationFeedback": OperationFeedback,
    }


def _cargar_grupo_acciones_y_estado() -> dict[str, Any]:
    import app.ui.vistas.main_window.acciones_pendientes as acciones_pendientes
    import app.ui.vistas.main_window.acciones_personas as acciones_personas
    import app.ui.vistas.main_window.acciones_sincronizacion as acciones_sincronizacion
    import app.ui.vistas.main_window.validacion_preventiva as validacion_preventiva
    from app.ui.toast_helpers import toast_error, toast_success
    from app.ui.vistas import historico_actions
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
    from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf
    from app.ui.vistas.solicitudes_presenter import ActionStateInput, build_action_state

    return {
        "acciones_pendientes": acciones_pendientes,
        "acciones_personas": acciones_personas,
        "acciones_sincronizacion": acciones_sincronizacion,
        "validacion_preventiva": validacion_preventiva,
        "toast_error": toast_error,
        "toast_success": toast_success,
        "historico_actions": historico_actions,
        "ActionStateInput": ActionStateInput,
        "build_action_state": build_action_state,
        "debe_habilitar_confirmar_pdf": debe_habilitar_confirmar_pdf,
        "ask_push_after_pdf": ask_push_after_pdf,
        "build_confirmation_payload": build_confirmation_payload,
        "execute_confirmar_with_pdf": execute_confirmar_with_pdf,
        "finalize_confirmar_with_pdf": finalize_confirmar_with_pdf,
        "iterar_pendientes_en_tabla": iterar_pendientes_en_tabla,
        "on_confirmar": on_confirmar,
        "on_insertar_sin_pdf": on_insertar_sin_pdf,
        "prompt_confirm_pdf_path": prompt_confirm_pdf_path,
        "show_confirmation_closure": show_confirmation_closure,
        "show_pdf_actions_dialog": show_pdf_actions_dialog,
        "sum_solicitudes_minutes": sum_solicitudes_minutes,
        "undo_confirmation": undo_confirmation,
    }


def _cargar_grupo_helpers_builders_y_sync() -> dict[str, Any]:
    from app.ui.components.saldos_card import SaldosCard
    from app.ui.patterns import (
        STATUS_PATTERNS,
        apply_modal_behavior,
        build_modal_actions,
        status_badge,
    )
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
    from app.ui.vistas.builders.main_window_builders import (
        build_main_window_widgets,
        build_shell_layout,
        build_status_bar,
    )
    from app.ui.vistas.init_refresh import run_init_refresh
    from app.ui.vistas.main_window_health_mixin import MainWindowHealthMixin
    from app.ui.vistas.main_window_helpers import (
        build_estado_pendientes_debug_payload,
        build_historico_filters_payload,
        handle_historico_render_mismatch,
        log_estado_pendientes,
        show_sync_error_dialog_from_exception,
    )
    from app.ui.vistas.ui_helpers import abrir_archivo_local
    from app.ui.workers.sincronizacion_workers import PushWorker

    return {
        "SaldosCard": SaldosCard,
        "PushWorker": PushWorker,
        "MainWindowHealthMixin": MainWindowHealthMixin,
        "apply_modal_behavior": apply_modal_behavior,
        "build_modal_actions": build_modal_actions,
        "status_badge": status_badge,
        "STATUS_PATTERNS": STATUS_PATTERNS,
        "build_config_incomplete_report": build_config_incomplete_report,
        "build_failed_report": build_failed_report,
        "build_simulation_report": build_simulation_report,
        "build_sync_report": build_sync_report,
        "list_sync_history": list_sync_history,
        "load_sync_report": load_sync_report,
        "persist_report": persist_report,
        "to_markdown": to_markdown,
        "run_init_refresh": run_init_refresh,
        "build_main_window_widgets": build_main_window_widgets,
        "build_shell_layout": build_shell_layout,
        "build_status_bar": build_status_bar,
        "abrir_archivo_local": abrir_archivo_local,
        "build_estado_pendientes_debug_payload": build_estado_pendientes_debug_payload,
        "build_historico_filters_payload": build_historico_filters_payload,
        "handle_historico_render_mismatch": handle_historico_render_mismatch,
        "log_estado_pendientes": log_estado_pendientes,
        "show_sync_error_dialog_from_exception": show_sync_error_dialog_from_exception,
    }


_FALLBACK_GRUPO_DIALOGOS: dict[str, Any] = {}

_FALLBACK_GRUPO_ACCIONES: dict[str, Any] = {
    "acciones_pendientes": object,
    "acciones_personas": object,
    "acciones_sincronizacion": object,
    "validacion_preventiva": object,
    "toast_error": _qt_unavailable,
    "toast_success": _qt_unavailable,
    "historico_actions": _HistoricoActionsFallback(),
    "ActionStateInput": object,
    "build_action_state": _qt_unavailable,
    "debe_habilitar_confirmar_pdf": _qt_unavailable,
    "ask_push_after_pdf": _qt_unavailable,
    "build_confirmation_payload": _qt_unavailable,
    "execute_confirmar_with_pdf": _qt_unavailable,
    "finalize_confirmar_with_pdf": _qt_unavailable,
    "iterar_pendientes_en_tabla": _qt_unavailable,
    "on_confirmar": _qt_unavailable,
    "on_insertar_sin_pdf": _qt_unavailable,
    "prompt_confirm_pdf_path": _qt_unavailable,
    "show_confirmation_closure": _qt_unavailable,
    "show_pdf_actions_dialog": _qt_unavailable,
    "sum_solicitudes_minutes": _qt_unavailable,
    "undo_confirmation": _qt_unavailable,
}

_FALLBACK_GRUPO_HELPERS: dict[str, Any] = {
    "STATUS_PATTERNS": {},
}


namespace_dialogos = _resolver_namespace_importaciones(
    _cargar_grupo_dialogos_y_controllers,
    _FALLBACK_GRUPO_DIALOGOS,
    nombre_grupo="dialogos",
    simbolos_criticos=SIMBOLOS_CRITICOS_POR_GRUPO["dialogos"],
)
namespace_acciones = _resolver_namespace_importaciones(
    _cargar_grupo_acciones_y_estado,
    _FALLBACK_GRUPO_ACCIONES,
    nombre_grupo="acciones",
)
namespace_helpers = _resolver_namespace_importaciones(
    _cargar_grupo_helpers_builders_y_sync,
    _FALLBACK_GRUPO_HELPERS,
    nombre_grupo="helpers",
    simbolos_criticos=SIMBOLOS_CRITICOS_POR_GRUPO["helpers"],
)

# Compatibilidad legacy mínima: mantener aliases usados por consumidores
# internos no migrados (state_controller) y puntos de integración externos.
GestorToasts = namespace_dialogos.GestorToasts
PersonasController = namespace_dialogos.PersonasController
SolicitudesController = namespace_dialogos.SolicitudesController
SyncController = namespace_dialogos.SyncController
PdfController = namespace_dialogos.PdfController
NotificationService = namespace_dialogos.NotificationService

PushWorker = namespace_helpers.PushWorker
SaldosCard = namespace_helpers.SaldosCard
MainWindowHealthMixin = namespace_helpers.MainWindowHealthMixin

# Compatibilidad pública adicional.
toast_error = namespace_acciones.toast_error
status_badge = namespace_helpers.status_badge
run_init_refresh = namespace_helpers.run_init_refresh

__all__ = [
    "namespace_dialogos",
    "namespace_acciones",
    "namespace_helpers",
    "ImportacionCriticaMainWindowError",
    "SIMBOLOS_CRITICOS_POR_GRUPO",
    "GestorToasts",
    "PersonasController",
    "SolicitudesController",
    "SyncController",
    "PdfController",
    "NotificationService",
    "PushWorker",
    "SaldosCard",
    "MainWindowHealthMixin",
    "toast_error",
    "status_badge",
    "run_init_refresh",
]
