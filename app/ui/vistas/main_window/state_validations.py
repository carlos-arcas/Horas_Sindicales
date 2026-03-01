from __future__ import annotations

import logging

try:
    from PySide6.QtWidgets import QMessageBox
except Exception:  # pragma: no cover
    QMessageBox = object

from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
from app.ui.notification_service import ConfirmationSummaryPayload
from app.ui.copy_catalog import copy_text
from app.ui.toast_helpers import toast_error, toast_success
from app.core.observability import OperationContext
from app.application.dto import SolicitudDTO
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

logger = logging.getLogger(__name__)


class MainWindowStateValidationMixin:
    def _handle_duplicate_detected(self, duplicate: SolicitudDTO) -> bool:
        is_pending = not duplicate.generated
        dialog = QMessageBox(self)
        dialog.setWindowTitle(copy_text("ui.validacion.solicitud_duplicada"))
        if is_pending:
            dialog.setText(copy_text("ui.validacion.duplicada_pendiente"))
            dialog.setInformativeText(copy_text("ui.validacion.duplicada_pendiente_info"))
            goto_button = dialog.addButton(copy_text("ui.validacion.ir_pendiente"), QMessageBox.AcceptRole)
        else:
            dialog.setText(copy_text("ui.validacion.duplicada_historico"))
            dialog.setInformativeText(copy_text("ui.validacion.duplicada_historico_info"))
            goto_button = dialog.addButton(copy_text("ui.validacion.ir_historico"), QMessageBox.AcceptRole)
        dialog.addButton(copy_text("ui.validacion.cancelar"), QMessageBox.RejectRole)
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

    def _resolve_backend_conflict(self, persona_id: int, solicitud: SolicitudDTO) -> bool:
        try:
            conflicto = self._solicitud_use_cases.validar_conflicto_dia(persona_id, solicitud.fecha_pedida, solicitud.completo)
        except BusinessRuleError as exc:
            self.toast.warning(str(exc), title=copy_text("ui.validacion.validacion"))
            return False
        if conflicto.ok:
            return True
        mensaje = copy_text("ui.validacion.sustituir_por_completo") if solicitud.completo else copy_text("ui.validacion.sustituir_por_franja")
        if not self._confirm_conflicto(mensaje):
            return False
        try:
            with OperationContext("sustituir_solicitud") as operation:
                method = self._solicitud_use_cases.sustituir_por_completo if solicitud.completo else self._solicitud_use_cases.sustituir_por_parcial
                method(persona_id, solicitud.fecha_pedida, solicitud, correlation_id=operation.correlation_id)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title=copy_text("ui.validacion.validacion"))
            return False
        except Exception as exc:
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

    def _execute_confirmar_with_pdf(self, persona, selected: list[SolicitudDTO], pdf_path: str):
        return execute_confirmar_with_pdf(self, persona, selected, pdf_path)

    def _finalize_confirmar_with_pdf(self, persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes) -> None:
        finalize_confirmar_with_pdf(self, persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes)

    def _toast_success(self, message: str, title: str | None = None) -> None:
        toast_success(self.toast, message, title=title)

    def _toast_error(self, message: str, title: str | None = None) -> None:
        toast_error(self.toast, message, title=title)

    def _show_pdf_actions_dialog(self, generated_path) -> None:
        show_pdf_actions_dialog(self, generated_path)

    def _sum_solicitudes_minutes(self, solicitudes: list[SolicitudDTO]) -> int:
        return sum_solicitudes_minutes(solicitudes)

    def _show_confirmation_closure(self, creadas, errores, *, operation_name: str, correlation_id: str | None = None) -> None:
        show_confirmation_closure(self, creadas, errores, operation_name=operation_name, correlation_id=correlation_id)

    def _build_confirmation_payload(self, creadas, errores, *, correlation_id: str | None = None) -> ConfirmationSummaryPayload:
        return build_confirmation_payload(self, creadas, errores, correlation_id=correlation_id)

    def _undo_confirmation(self, solicitud_ids: list[int]) -> None:
        undo_confirmation(self, solicitud_ids)

    def _ask_push_after_pdf(self) -> None:
        ask_push_after_pdf(self)

    def _show_critical_error(self, error: Exception | str) -> None:
        mapped = UiErrorMessage(title=copy_text("ui.validacion.error"), probable_cause=error, recommended_action=copy_text("ui.validacion.reintentar_soporte"), severity="blocking") if isinstance(error, str) else map_error_to_ui_message(error)
        if isinstance(error, BusinessRuleError):
            mapped.title = copy_text("ui.validacion.validacion")
            mapped.probable_cause = str(error)
            mapped.recommended_action = copy_text("ui.validacion.corrige_dato")
        if not isinstance(error, str):
            logger.exception("Error técnico capturado en UI", exc_info=error, extra={"correlation_id": mapped.incident_id})
        message = mapped.as_text()
        self._solicitudes_runtime_error = True
        self._update_solicitudes_status_panel()
        self._toast_error(message, title=copy_text("ui.validacion.error"))
        QMessageBox.critical(self, mapped.title, message)

    def _show_error_detail(self, *, titulo: str, mensaje: str, incident_id: str | None = None, correlation_id: str | None = None, stack: str | None = None) -> None:
        payload = {"mensaje": mensaje, "incident_id": incident_id or copy_text("ui.validacion.no_disponible_abrev"), "correlation_id": correlation_id or copy_text("ui.validacion.no_disponible_abrev"), "resumen": stack or copy_text("ui.validacion.sin_detalle_tecnico")}
        dialog = self._historico_detalle_dialog_class(payload, self)
        dialog.setWindowTitle(titulo)
        dialog.exec()

    def _show_optional_notice(self, key: str, title: str, message: str) -> None:
        if bool(self._settings.value(key, False, type=bool)):
            self.toast.info(message, title=title)
            return
        dialog = self._optional_confirm_dialog_class(title, message, self)
        dialog.exec()
        if dialog.skip_next_check.isChecked():
            self._settings.setValue(key, True)
        self.toast.info(message, title=title)

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return QMessageBox.question(self, copy_text("ui.validacion.conflicto"), mensaje, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
