from __future__ import annotations

from dataclasses import dataclass

from app.application.conflicts_service import ConflictRecord


@dataclass(frozen=True)
class ModeloVistaConflictoFila:
    record: ConflictRecord
    tipo: str
    fecha: str
    campo: str
    local_updated: str
    remote_updated: str


@dataclass(frozen=True)
class ModeloVistaResumenPanel:
    texto: str


@dataclass(frozen=True)
class ModeloVistaResumenResolucion:
    resueltos: int
    pendientes: int
    revision_manual: int
