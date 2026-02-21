from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EstadoCheck(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NO_EVALUABLE = "NO_EVALUABLE"


class SeveridadCheck(str, Enum):
    ALTO = "ALTO"
    MEDIO = "MEDIO"
    BAJO = "BAJO"


@dataclass(frozen=True)
class CheckAuditoria:
    id_check: str
    estado: EstadoCheck
    severidad: SeveridadCheck
    evidencia: list[str]
    recomendacion: str


@dataclass(frozen=True)
class RequestAuditoriaE2E:
    dry_run: bool = True
    id_auditoria: str | None = None


@dataclass(frozen=True)
class PlanAuditoria:
    id_auditoria: str
    fecha_utc: datetime
    dry_run: bool
    checks_objetivo: list[str]


@dataclass(frozen=True)
class RutasAuditoria:
    base_dir: str
    informe_md: str
    informe_json: str
    manifest_json: str
    status_txt: str


@dataclass(frozen=True)
class ConflictosAuditoria:
    conflictos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResultadoAuditoria:
    id_auditoria: str
    dry_run: bool
    resultado_global: str
    exit_code: int
    score: float
    checks: list[CheckAuditoria]
    rutas_previstas: RutasAuditoria
    conflictos: list[str]
    contenido_md: str
    contenido_json: dict
    artefactos_generados: list[str]
