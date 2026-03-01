from __future__ import annotations

import logging

try:
    from PySide6.QtWidgets import QMessageBox
except Exception:  # pragma: no cover
    QMessageBox = object

from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.error_mapping import UiErrorMessage, map_error_to_ui_message
from app.ui.notification_service import ConfirmationSummaryPayload
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

    def _resolve_backend_conflict(self, persona_id: int, solicitud: SolicitudDTO) -> bool:
        try:
            conflicto = self._solicitud_use_cases.validar_conflicto_dia(persona_id, solicitud.fecha_pedida, solicitud.completo)
        except BusinessRuleError as exc:
            self.toast.warning(str(exc), title="Validación")
            return False
        if conflicto.ok:
            return True
        mensaje = "Hay horas parciales. ¿Sustituirlas por COMPLETO?" if solicitud.completo else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
        if not self._confirm_conflicto(mensaje):
            return False
        try:
            with OperationContext("sustituir_solicitud") as operation:
                method = self._solicitud_use_cases.sustituir_por_completo if solicitud.completo else self._solicitud_use_cases.sustituir_por_parcial
                method(persona_id, solicitud.fecha_pedida, solicitud, correlation_id=operation.correlation_id)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
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
        mapped = UiErrorMessage(title="Error", probable_cause=error, recommended_action="Reintentar. Si persiste, contactar con soporte.", severity="blocking") if isinstance(error, str) else map_error_to_ui_message(error)
        if isinstance(error, BusinessRuleError):
            mapped.title = "Validación"
            mapped.probable_cause = str(error)
            mapped.recommended_action = "Corrige el dato indicado y vuelve a intentarlo."
        if not isinstance(error, str):
            logger.exception("Error técnico capturado en UI", exc_info=error, extra={"correlation_id": mapped.incident_id})
        message = mapped.as_text()
        self._solicitudes_runtime_error = True
        self._update_solicitudes_status_panel()
        self._toast_error(message, title="Error")
        QMessageBox.critical(self, mapped.title, message)

    def _show_error_detail(self, *, titulo: str, mensaje: str, incident_id: str | None = None, correlation_id: str | None = None, stack: str | None = None) -> None:
        payload = {"mensaje": mensaje, "incident_id": incident_id or "N/D", "correlation_id": correlation_id or "N/D", "resumen": stack or "Sin detalle técnico"}
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
        return QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
