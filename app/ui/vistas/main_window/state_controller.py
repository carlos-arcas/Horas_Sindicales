from __future__ import annotations

from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf
from app.ui.vistas.solicitudes_presenter import ActionStateInput, build_action_state


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
