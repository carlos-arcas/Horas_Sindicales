from __future__ import annotations

from typing import Any


def resolve_active_delegada_id(delegada_ids: list[int], preferred_id: object) -> int | None:
    """Resuelve una delegada activa priorizando la preferencia si es válida."""
    if not delegada_ids:
        return None
    try:
        preferred = int(preferred_id) if preferred_id is not None else None
    except (TypeError, ValueError):
        preferred = None
    if preferred is not None and preferred in delegada_ids:
        return preferred
    return delegada_ids[0]


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
    selected_rows: list[int] = []
    selected_pending = getattr(window, "_selected_pending_row_indexes", None)
    if callable(selected_pending):
        selected_rows = selected_pending() or []

    has_persona = False
    current_persona = getattr(window, "_current_persona", None)
    if callable(current_persona):
        has_persona = current_persona() is not None

    has_pending = bool(getattr(window, "_pending_solicitudes", []))
    has_selection = bool(selected_rows)
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
