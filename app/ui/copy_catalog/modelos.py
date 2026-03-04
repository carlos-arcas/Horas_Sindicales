from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntradaCatalogo:
    clave: str
    texto: str


@dataclass(frozen=True)
class CambioCatalogo:
    clave: str
    texto_base: str
    texto_objetivo: str


@dataclass(frozen=True)
class ResultadoDiff:
    missing: tuple[EntradaCatalogo, ...]
    extra: tuple[EntradaCatalogo, ...]
    changed: tuple[CambioCatalogo, ...]
