from __future__ import annotations

from app.core.errors import BusinessError, InfraError


def map_error_to_user_message(error: Exception) -> str:
    if isinstance(error, BusinessError):
        return str(error)
    if isinstance(error, InfraError):
        return "Se produjo un error técnico. Inténtalo de nuevo o revisa los logs."
    return "Se produjo un error inesperado. Inténtalo de nuevo."
