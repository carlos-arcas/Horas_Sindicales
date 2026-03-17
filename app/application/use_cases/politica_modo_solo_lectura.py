from __future__ import annotations

from app.configuracion.settings import is_read_only_enabled
from app.domain.services import BusinessRuleError

MENSAJE_MODO_SOLO_LECTURA = "Modo solo lectura activado"


def verificar_modo_solo_lectura() -> None:
    """Bloquea operaciones mutantes cuando la aplicación está en modo solo lectura."""
    if is_read_only_enabled():
        raise BusinessRuleError(MENSAJE_MODO_SOLO_LECTURA)
