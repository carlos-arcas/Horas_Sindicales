from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ErrorTransicionPostLogin:
    reason_code: str
    exc_type: str


def debe_mantener_referencia_ventana_principal(ventana: object | None) -> bool:
    return ventana is not None


class ControladorSesionInterfaz:
    def __init__(self) -> None:
        self.ventana_principal: object | None = None

    def guardar_ventana_principal(self, ventana: object | None) -> bool:
        if not debe_mantener_referencia_ventana_principal(ventana):
            return False
        self.ventana_principal = ventana
        return True


def ejecutar_transicion_post_login(
    *,
    crear_ventana_principal: Callable[[], object],
    registrar_ventana_principal: Callable[[object], bool],
    mostrar_ventana_principal: Callable[[object], None],
    registrar_evento: Callable[[str, dict[str, object]], None],
    informar_error: Callable[[ErrorTransicionPostLogin], bool],
) -> bool:
    while True:
        registrar_evento("auth_login_accepted", {})
        registrar_evento("main_window_create", {})
        try:
            ventana = crear_ventana_principal()
            if not registrar_ventana_principal(ventana):
                raise ValueError("main_window_reference_not_stored")
            registrar_evento("main_window_show", {})
            mostrar_ventana_principal(ventana)
            registrar_evento("post_login_transition_ok", {})
            return True
        except Exception as exc:  # noqa: BLE001
            reason_code = _resolver_reason_code(exc)
            error = ErrorTransicionPostLogin(
                reason_code=reason_code,
                exc_type=type(exc).__name__,
            )
            registrar_evento(
                "post_login_transition_fail",
                {
                    "reason_code": error.reason_code,
                    "exc_type": error.exc_type,
                },
            )
            if not informar_error(error):
                return False


def _resolver_reason_code(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return "dependency_wiring_failed"
    if isinstance(exc, (RuntimeError, TypeError)):
        return "main_window_init_failed"
    return "unexpected_error"

