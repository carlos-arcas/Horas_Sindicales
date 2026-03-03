from __future__ import annotations

from typing import Any

from app.ui.vistas.personas_presenter import resolve_active_delegada_id as _resolver_delegada_activa


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
            bar.showMessage("Procesando..." if in_progress else "", 0 if in_progress else 2000)


def update_action_state(window: Any) -> None:
    """Sincroniza habilitación de acciones según estado actual del formulario."""
    selected_historico_ids = set(getattr(window, "_historico_ids_seleccionados", set()))

    has_persona = False
    current_persona = getattr(window, "_current_persona", None)
    if callable(current_persona):
        has_persona = current_persona() is not None

    has_pending = bool(getattr(window, "_pending_solicitudes", []))
    has_selection = bool(selected_historico_ids)
    has_blocking_errors = bool(getattr(window, "_blocking_errors", {}))
    sync_in_progress = bool(getattr(window, "_sync_in_progress", False))

    valid_form = False
    validate_form = getattr(window, "_validate_solicitud_form", None)
    if callable(validate_form):
        try:
            valid_form, _ = validate_form()
        except Exception:
            valid_form = False

    add_enabled = has_persona and valid_form and not has_blocking_errors and not sync_in_progress
    confirm_enabled = has_pending and not has_blocking_errors and not sync_in_progress
    remove_enabled = has_selection and not sync_in_progress

    actions = {
        "agregar_button": add_enabled,
        "confirmar_button": confirm_enabled,
        "eliminar_button": remove_enabled,
        "clear_button": has_pending and not sync_in_progress,
    }
    for control_name, enabled in actions.items():
        control = getattr(window, control_name, None)
        if control is None:
            continue
        setter = getattr(control, "setEnabled", None)
        if callable(setter):
            setter(enabled)

    refresh_status_panel = getattr(window, "_update_solicitudes_status_panel", None)
    if callable(refresh_status_panel):
        refresh_status_panel()
