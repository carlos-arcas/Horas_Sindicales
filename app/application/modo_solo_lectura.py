from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EstadoModoSoloLectura:
    proveedor_activo: Callable[[], bool]

    def esta_activo(self) -> bool:
        return self.proveedor_activo()


def crear_estado_modo_solo_lectura(
    proveedor_activo: Callable[[], bool],
) -> EstadoModoSoloLectura:
    return EstadoModoSoloLectura(proveedor_activo=proveedor_activo)
