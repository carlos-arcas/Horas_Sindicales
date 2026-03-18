from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from app.domain.services import BusinessRuleError

MENSAJE_MODO_SOLO_LECTURA = "Modo solo lectura activado"

ProveedorModoSoloLectura = Callable[[], bool]


def modo_solo_lectura_por_entorno() -> bool:
    valor = os.environ.get("READ_ONLY", "").strip().lower()
    return valor in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PoliticaModoSoloLectura:
    proveedor_activo: ProveedorModoSoloLectura

    def verificar(self) -> None:
        """Bloquea operaciones mutantes cuando la aplicación está en modo solo lectura."""
        if self.proveedor_activo():
            raise BusinessRuleError(MENSAJE_MODO_SOLO_LECTURA)


def crear_politica_modo_solo_lectura(
    proveedor: ProveedorModoSoloLectura = modo_solo_lectura_por_entorno,
) -> PoliticaModoSoloLectura:
    return PoliticaModoSoloLectura(proveedor_activo=proveedor)
