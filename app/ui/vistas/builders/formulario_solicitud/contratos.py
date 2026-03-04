from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TarjetaSeccion:
    card: object
    layout: object
