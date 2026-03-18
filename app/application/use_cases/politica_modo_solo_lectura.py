from __future__ import annotations

from dataclasses import dataclass

from app.application.modo_solo_lectura import (
    EstadoModoSoloLectura,
    crear_estado_modo_solo_lectura,
)
from app.domain.services import BusinessRuleError

MENSAJE_MODO_SOLO_LECTURA = "Modo solo lectura activado"


@dataclass(frozen=True)
class PoliticaModoSoloLectura:
    estado: EstadoModoSoloLectura

    def verificar(self) -> None:
        """Bloquea operaciones mutantes cuando la aplicación está en modo solo lectura."""
        if self.estado.esta_activo():
            raise BusinessRuleError(MENSAJE_MODO_SOLO_LECTURA)


def crear_politica_modo_solo_lectura(
    estado: EstadoModoSoloLectura,
) -> PoliticaModoSoloLectura:
    return PoliticaModoSoloLectura(estado=estado)


__all__ = [
    "EstadoModoSoloLectura",
    "MENSAJE_MODO_SOLO_LECTURA",
    "PoliticaModoSoloLectura",
    "crear_estado_modo_solo_lectura",
    "crear_politica_modo_solo_lectura",
]
