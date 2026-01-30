from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PersonaDTO:
    id: Optional[int]
    nombre: str
    genero: str
    horas_mes: float
    horas_ano: float
    horas_jornada_defecto: float
    cuad_lun: float
    cuad_mar: float
    cuad_mie: float
    cuad_jue: float
    cuad_vie: float
    cuad_sab: float
    cuad_dom: float


@dataclass(frozen=True)
class SolicitudDTO:
    id: Optional[int]
    persona_id: int
    fecha_solicitud: str
    fecha_pedida: str
    desde: Optional[str]
    hasta: Optional[str]
    completo: bool
    horas: float
    observaciones: Optional[str]
    pdf_path: Optional[str]
    pdf_hash: Optional[str]


@dataclass(frozen=True)
class SaldosDTO:
    consumidas_mes: int
    restantes_mes: int
    consumidas_ano: int
    restantes_ano: int
    exceso_mes: int
    exceso_ano: int
    excedido_mes: bool
    excedido_ano: bool


@dataclass(frozen=True)
class PeriodoFiltro:
    modo: str
    year: int
    month: Optional[int] = None

    @classmethod
    def anual(cls, year: int) -> PeriodoFiltro:
        return cls(modo="ANUAL", year=year, month=None)

    @classmethod
    def mensual(cls, year: int, month: int) -> PeriodoFiltro:
        return cls(modo="MENSUAL", year=year, month=month)


@dataclass(frozen=True)
class TotalesGlobalesDTO:
    total_consumidas_min: int
    total_bolsa_min: int
    total_restantes_min: int
