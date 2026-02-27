from __future__ import annotations


def _main_window_real_class():
    from app.ui.vistas.main_window_vista import MainWindow as MainWindowVista

    return MainWindowVista


class MainWindow:
    """Proxy liviano para mantener la API pública estable."""

    def __new__(cls, *args, **kwargs):
        return _main_window_real_class()(*args, **kwargs)

    def _update_action_state(self) -> None:
        if hasattr(self, "_run_preventive_validation"):
            self._run_preventive_validation()
        persona_selected = self._current_persona() is not None
        form_valid, form_message = self._validate_solicitud_form()
        blocking_errors = getattr(self, "_blocking_errors", {})
        has_blocking_errors = bool(blocking_errors)
        first_blocking_error = next(iter(blocking_errors.values()), "")
        self.agregar_button.setEnabled(persona_selected and form_valid and not has_blocking_errors)
        has_pending = bool(self._pending_solicitudes)
        can_confirm = has_pending and not self._pending_conflict_rows and not self._pending_view_all and not has_blocking_errors
        self.insertar_sin_pdf_button.setEnabled(persona_selected and can_confirm)
        selected_pending = self._selected_pending_solicitudes()
        self.confirmar_button.setEnabled(persona_selected and can_confirm and bool(selected_pending))
        self.edit_persona_button.setEnabled(persona_selected)
        self.delete_persona_button.setEnabled(persona_selected)
        self.edit_grupo_button.setEnabled(True)
        self.editar_pdf_button.setEnabled(True)
        selected_historico = self._selected_historico_solicitudes()
        self.eliminar_button.setEnabled(persona_selected and bool(selected_historico))
        self.eliminar_pendiente_button.setEnabled(bool(self._pending_solicitudes))
        self.generar_pdf_button.setEnabled(persona_selected and bool(selected_historico))
        selected_count = len(selected_historico)
        self.eliminar_button.setText(f"Eliminar ({selected_count})")
        self.generar_pdf_button.setText(f"Exportar histórico PDF ({selected_count})")
        if hasattr(self, "_sync_historico_select_all_visible_state"):
            self._sync_historico_select_all_visible_state()


        self._update_stepper_state(form_valid, has_blocking_errors, first_blocking_error, form_message)

        active_step = self._resolve_operativa_step(form_valid and not has_blocking_errors, has_pending, selected_pending, can_confirm)
        self._set_operativa_step(active_step)
        self._update_step_context(active_step)
        self._update_confirmation_summary(selected_pending)

    def _update_stepper_state(
        self,
        form_valid: bool,
        has_blocking_errors: bool,
        first_blocking_error: str,
        form_message: str,
    ) -> None:
        form_step_valid = form_valid and not has_blocking_errors
        self.stepper_labels[1].setEnabled(form_step_valid)
        stepper_message = first_blocking_error or form_message or "Completa la solicitud para poder añadirla"
        self.stepper_labels[1].setToolTip("" if form_step_valid else stepper_message)


__all__ = ["MainWindow"]
