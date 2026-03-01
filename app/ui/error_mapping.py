from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import BusinessError, InfraError
from app.core.observability import get_correlation_id
from app.ui.copy_catalog import copy_text


@dataclass(frozen=True)
class UiErrorMessage:
    title: str
    probable_cause: str
    recommended_action: str
    severity: str

    incident_id: str | None = None

    def as_text(self) -> str:
        body = (
            f"{self.title}\n"
            f"{copy_text('ui.errores.causa_probable_label')} {self.probable_cause}\n"
            f"{copy_text('ui.conflictos.accion_recomendada_label')} {self.recommended_action}"
        )
        if self.incident_id:
            body = f"{body}\n{copy_text('ui.errores.id_incidente_label')} {self.incident_id}"
        return body


def map_error_to_ui_message(error: Exception, *, incident_id: str | None = None) -> UiErrorMessage:
    resolved_incident_id = incident_id or get_correlation_id()
    if isinstance(error, BusinessError):
        message = str(error).strip() or copy_text("ui.errores.no_se_pudo_completar_operacion")
        return UiErrorMessage(
            title=message,
            probable_cause=copy_text("ui.errores.regla_negocio_probable"),
            recommended_action=copy_text("ui.errores.corregir_datos_reintentar"),
            severity="warning",
            incident_id=resolved_incident_id,
        )
    if isinstance(error, InfraError):
        return UiErrorMessage(
            title=copy_text("ui.errores.no_se_pudo_completar_operacion"),
            probable_cause=copy_text("ui.errores.no_fue_posible_acceder_datos"),
            recommended_action=copy_text("ui.errores.reintenta_revision_config_soporte"),
            severity="blocking",
            incident_id=resolved_incident_id,
        )
    return UiErrorMessage(
        title=copy_text("ui.errores.error_inesperado"),
        probable_cause=copy_text("ui.errores.fallo_tecnico_no_identificado"),
        recommended_action=copy_text("ui.errores.reintenta_contacta_soporte"),
        severity="blocking",
        incident_id=resolved_incident_id,
    )


def map_error_to_user_message(error: Exception, *, incident_id: str | None = None) -> str:
    return map_error_to_ui_message(error, incident_id=incident_id).as_text()
