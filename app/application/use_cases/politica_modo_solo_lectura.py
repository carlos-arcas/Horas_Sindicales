from __future__ import annotations

import os
from collections.abc import Callable

from app.domain.services import BusinessRuleError

MENSAJE_MODO_SOLO_LECTURA = "Modo solo lectura activado"

ProveedorModoSoloLectura = Callable[[], bool]


def _proveedor_modo_solo_lectura_por_entorno() -> bool:
    valor = os.environ.get("READ_ONLY", "").strip().lower()
    return valor in {"1", "true", "yes", "on"}


_proveedor_modo_solo_lectura: ProveedorModoSoloLectura = (
    _proveedor_modo_solo_lectura_por_entorno
)


def configurar_proveedor_modo_solo_lectura(
    proveedor: ProveedorModoSoloLectura,
) -> None:
    """Configura quién decide si el modo solo lectura está activo."""
    global _proveedor_modo_solo_lectura
    _proveedor_modo_solo_lectura = proveedor


def restablecer_proveedor_modo_solo_lectura() -> None:
    """Restaura el proveedor por defecto basado en entorno."""
    configurar_proveedor_modo_solo_lectura(_proveedor_modo_solo_lectura_por_entorno)


def verificar_modo_solo_lectura() -> None:
    """Bloquea operaciones mutantes cuando la aplicación está en modo solo lectura."""
    if _proveedor_modo_solo_lectura():
        raise BusinessRuleError(MENSAJE_MODO_SOLO_LECTURA)
