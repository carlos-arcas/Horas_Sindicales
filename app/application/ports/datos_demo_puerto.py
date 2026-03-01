from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResultadoCargaDemoPuerto:
    ok: bool
    mensaje_usuario: str
    detalles: str | None = None
    warnings: tuple[str, ...] = ()
    acciones_sugeridas: tuple[str, ...] = ()


class CargadorDatosDemoPuerto(Protocol):
    def cargar(self, modo: str) -> ResultadoCargaDemoPuerto:
        ...
