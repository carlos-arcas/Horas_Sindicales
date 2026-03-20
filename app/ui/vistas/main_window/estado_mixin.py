from __future__ import annotations

import logging

from app.ui.copy_catalog import copy_text

from . import acciones_personas, acciones_sincronizacion

logger = logging.getLogger(__name__)


class EstadoMainWindowMixin:
    def _save_current_draft(self, persona_id: int | None) -> None:
        return acciones_personas.save_current_draft(self, persona_id)

    def _is_form_dirty(self) -> bool:
        return acciones_personas.is_form_dirty(self)

    def _confirmar_cambio_delegada(self, *_args: object) -> bool:
        return acciones_personas.confirmar_cambio_delegada(self)

    def _restore_draft_for_persona(self, persona_id: int | None) -> None:
        return acciones_personas.restore_draft_for_persona(self, persona_id)

    def _load_personas(self) -> None:
        return acciones_personas.load_personas(self)

    def _current_persona(self):
        return acciones_personas.current_persona(self)

    def _on_persona_changed(self) -> None:
        return acciones_personas.on_persona_changed(self)

    def _on_add_persona(self) -> None:
        return acciones_personas.on_add_persona(self)

    def _on_edit_persona(self) -> None:
        return acciones_personas.on_edit_persona(self)

    def _on_delete_persona(self) -> None:
        return acciones_personas.on_delete_persona(self)

    def _sync_config_persona_actions(self) -> None:
        return acciones_personas.sync_config_persona_actions(self)

    def _selected_config_persona(self):
        return acciones_personas.selected_config_persona(self)

    def _on_config_delegada_changed(self, *_args: object) -> None:
        return acciones_personas.on_config_delegada_changed(self)

    def _restaurar_contexto_guardado(self) -> None:
        return acciones_personas.restaurar_contexto_guardado(self)

    def _set_sync_in_progress(self, en_progreso: bool) -> None:
        self._sync_in_progress = en_progreso
        try:
            acciones_sincronizacion.set_sync_in_progress(self, en_progreso)
            return
        except Exception:
            logger.warning("sync_in_progress_ui_update_failed", extra={"in_progress": en_progreso}, exc_info=True)
        for button_name in ("sync_button", "simulate_sync_button", "confirm_sync_button", "retry_failed_button"):
            button = vars(self).get(button_name)
            set_enabled = getattr(button, "setEnabled", None)
            if callable(set_enabled):
                set_enabled(not en_progreso)

    def _set_sync_status_badge(self, status: str) -> None:
        try:
            acciones_sincronizacion.set_sync_status_badge(self, status)
            return
        except Exception:
            logger.warning("sync_status_badge_update_failed", extra={"status": status}, exc_info=True)
        badge = vars(self).get("sync_status_badge")
        set_text = getattr(badge, "setText", None)
        if callable(set_text):
            set_text(self._status_to_label(status))

    def _handle_duplicate_detected(self, duplicate: object) -> bool:
        logger.info("duplicate_detected_abort", extra={"duplicate_type": type(duplicate).__name__})
        notifier = getattr(self, "notifications", None)
        notify_validation_error = getattr(notifier, "notify_validation_error", None)
        if callable(notify_validation_error):
            notify_validation_error(
                what=copy_text("ui.validacion.solicitud_duplicada"),
                why=copy_text("ui.validacion.duplicada_pendiente"),
                how=copy_text("ui.validacion.duplicada_pendiente_info"),
            )
            return False
        toast_warning = getattr(getattr(self, "toast", None), "warning", None)
        if callable(toast_warning):
            toast_warning(copy_text("ui.validacion.duplicada_pendiente"), title=copy_text("ui.validacion.solicitud_duplicada"))
        return False

    def _resolve_backend_conflict(self, persona_id: int, solicitud: object) -> bool:
        logger.debug("backend_conflict_check_passthrough", extra={"persona_id": persona_id, "solicitud_type": type(solicitud).__name__})
        return True
