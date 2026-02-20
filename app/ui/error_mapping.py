from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import BusinessError, InfraError


@dataclass(frozen=True)
class UiErrorMessage:
    title: str
    probable_cause: str
    recommended_action: str
    severity: str

    def as_text(self) -> str:
        return (
            f"{self.title}\n"
            f"Causa probable: {self.probable_cause}\n"
            f"Acción recomendada: {self.recommended_action}"
        )


def map_error_to_ui_message(error: Exception) -> UiErrorMessage:
    if isinstance(error, BusinessError):
        message = str(error).strip() or "No se pudo completar la operación"
        return UiErrorMessage(
            title=message,
            probable_cause="Los datos ingresados no cumplen una regla de negocio.",
            recommended_action="Corrige los datos marcados y reintenta.",
            severity="warning",
        )
    if isinstance(error, InfraError):
        return UiErrorMessage(
            title="No se pudo completar la operación",
            probable_cause="No fue posible acceder a los datos o al servicio externo.",
            recommended_action="Reintenta. Si persiste, revisa la configuración o contacta soporte.",
            severity="blocking",
        )
    return UiErrorMessage(
        title="Ocurrió un error inesperado.",
        probable_cause="Se produjo un fallo técnico no identificado.",
        recommended_action="Reintenta. Si persiste, contacta soporte.",
        severity="blocking",
    )


def map_error_to_user_message(error: Exception) -> str:
    return map_error_to_ui_message(error).as_text()
