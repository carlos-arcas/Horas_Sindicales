from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoArranqueDTO:
    """Datos puros calculados en el worker de arranque."""

    idioma_inicial: str
    pantalla_completa_inicial: bool
    necesita_onboarding: bool
