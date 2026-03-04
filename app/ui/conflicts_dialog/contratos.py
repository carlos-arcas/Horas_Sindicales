from __future__ import annotations

from dataclasses import dataclass

from app.application.conflicts_service import ConflictRecord


@dataclass(frozen=True)
class ViewModelConflictoFila:
    record: ConflictRecord
    tipo: str
    fecha: str
    campo: str
    local_updated: str
    remote_updated: str


@dataclass(frozen=True)
class ViewModelResumenPanel:
    texto: str


@dataclass(frozen=True)
class ViewModelResumenResolucion:
    resueltos: int
    pendientes: int
    revision_manual: int
