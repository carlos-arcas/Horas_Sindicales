from __future__ import annotations

from typing import Any

from app.ui.copy_catalog import copy_text
from app.ui.vistas.personas_presenter import resolve_active_delegada_id as _resolver_delegada_activa

from .estado_acciones import (
    EntradaEstadoAccionesMainWindow,
    resolver_estado_acciones_main_window,
)


def resolve_active_delegada_id(window: Any, preferred_id: object | None = None) -> int | None:
    """Resuelve la delegada activa desde una ventana o desde una lista de ids."""
    if isinstance(window, list):
        return _resolver_delegada_activa(window, preferred_id)

    combo = getattr(window, "persona_combo", None)
    delegada_ids: list[int] = []
    if combo is not None and hasattr(combo, "count") and hasattr(combo, "itemData"):
        delegada_ids = [combo.itemData(index) for index in range(combo.count()) if combo.itemData(index) is not None]
    if not delegada_ids:
        return None
    preferred = preferred_id if preferred_id is not None else getattr(window, "_last_persona_id", None)
    return _resolver_delegada_activa(delegada_ids, preferred)


def set_processing_state(window: Any, in_progress: bool) -> None:
    """Activa/desactiva estado de procesamiento en controles críticos de la UI."""
    controls = (
        "agregar_button",
        "confirmar_button",
        "eliminar_button",
        "limpiar_pendientes_button",
        "pendientes_table",
    )
    for control_name in controls:
        control = getattr(window, control_name, None)
        if control is None:
            continue
        setter = getattr(control, "setEnabled", None)
        if callable(setter):
            setter(not in_progress)

    status_bar = getattr(window, "statusBar", None)
    if callable(status_bar):
        bar = status_bar()
        if bar is not None and hasattr(bar, "showMessage"):
            bar.showMessage(
                copy_text("ui.validacion.procesando") if in_progress else "",
                0 if in_progress else 2000,
            )


def update_action_state(window: Any) -> None:
    """Sincroniza habilitación de acciones según estado actual del formulario."""
    form_valid, _form_message = window._validate_solicitud_form()
    estado = resolver_estado_acciones_main_window(
        EntradaEstadoAccionesMainWindow(
            persona_seleccionada=window._current_persona() is not None,
            formulario_valido=form_valid,
            hay_errores_bloqueantes=bool(window._blocking_errors),
            hay_pendientes_visibles=bool(window._pending_solicitudes),
            hay_conflictos_pendientes=bool(window._pending_conflict_rows),
            ver_todas_delegadas=bool(window._pending_view_all),
            sync_en_progreso=bool(window._sync_in_progress),
            cantidad_seleccion_pendientes=len(window._selected_pending_solicitudes()),
            cantidad_seleccion_historico=len(window._selected_historico_solicitudes()),
            cantidad_ids_historico_seleccionados=len(window._historico_ids_seleccionados),
            cantidad_pendientes_otras_delegadas=len(window._pending_otras_delegadas),
        )
    )

    _aplicar_habilitacion_controles(window, estado)
    _actualizar_textos_historico(window, estado.total_historico_seleccionado)

    refresh_status_panel = getattr(window, "_update_solicitudes_status_panel", None)
    if callable(refresh_status_panel):
        refresh_status_panel()


def _aplicar_habilitacion_controles(window: Any, estado: Any) -> None:
    acciones = {
        "agregar_button": estado.agregar_habilitado,
        "insertar_sin_pdf_button": estado.insertar_sin_pdf_habilitado,
        "confirmar_button": estado.confirmar_habilitado,
        "edit_persona_button": estado.editar_persona_habilitado,
        "delete_persona_button": estado.eliminar_persona_habilitado,
        "edit_grupo_button": estado.editar_grupo_habilitado,
        "editar_pdf_button": estado.editar_pdf_habilitado,
        "eliminar_button": estado.eliminar_historico_habilitado,
        "eliminar_pendiente_button": estado.eliminar_pendiente_habilitado,
        "generar_pdf_button": estado.generar_pdf_habilitado,
        "clear_button": estado.clear_habilitado,
    }
    for control_name, habilitado in acciones.items():
        control = getattr(window, control_name, None)
        if control is None:
            continue
        setter = getattr(control, "setEnabled", None)
        if callable(setter):
            setter(habilitado)


def _actualizar_textos_historico(window: Any, total_historico_seleccionado: int) -> None:
    _actualizar_texto_boton_historico(
        window,
        "eliminar_button",
        "ui.historico.eliminar_boton",
        total_historico_seleccionado,
    )
    _actualizar_texto_boton_historico(
        window,
        "generar_pdf_button",
        "ui.historico.exportar_pdf_boton",
        total_historico_seleccionado,
    )


def _actualizar_texto_boton_historico(
    window: Any,
    boton_attr: str,
    copy_key: str,
    total_historico_seleccionado: int,
) -> None:
    boton = getattr(window, boton_attr, None)
    if boton is None or not hasattr(boton, "setText"):
        return
    boton.setText(copy_text(copy_key).format(n=total_historico_seleccionado))
