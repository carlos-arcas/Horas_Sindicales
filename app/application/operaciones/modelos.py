from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlanOperacion:
    operacion: str
    dry_run: bool
    descripcion: str
    artefactos_previstos: list[str] = field(default_factory=list)
    directorios_previstos: list[str] = field(default_factory=list)
    metadatos: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RutasOperacion:
    base_dir: str | None = None
    archivos: list[str] = field(default_factory=list)
    directorios: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConflictosOperacion:
    conflictos: list[str] = field(default_factory=list)
    no_ejecutable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResultadoOperacion:
    operacion: str
    dry_run: bool
    plan: PlanOperacion
    rutas: RutasOperacion
    conflictos: ConflictosOperacion
    artefactos_generados: list[str] = field(default_factory=list)
    mensaje: str | None = None
    detalles: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
