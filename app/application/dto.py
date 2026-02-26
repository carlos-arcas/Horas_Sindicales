from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class _FechaAlias(str):
    """Alias transitorio: compara igual contra fecha_pedida y fecha_solicitud."""

    def __new__(cls, primary: str, secondary: str) -> "_FechaAlias":
        obj = str.__new__(cls, primary)
        obj._secondary = secondary
        return obj

    def __eq__(self, other: object) -> bool:
        return str.__eq__(self, other) or other == self._secondary


@dataclass(frozen=True)
class PersonaDTO:
    id: Optional[int]
    nombre: str
    genero: str
    horas_mes: int
    horas_ano: int
    is_active: bool
    cuad_lun_man_min: int
    cuad_lun_tar_min: int
    cuad_mar_man_min: int
    cuad_mar_tar_min: int
    cuad_mie_man_min: int
    cuad_mie_tar_min: int
    cuad_jue_man_min: int
    cuad_jue_tar_min: int
    cuad_vie_man_min: int
    cuad_vie_tar_min: int
    cuad_sab_man_min: int
    cuad_sab_tar_min: int
    cuad_dom_man_min: int
    cuad_dom_tar_min: int
    cuadrante_uniforme: bool = False
    trabaja_finde: bool = False


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
    notas: Optional[str] = None
    generated: bool = False

    @property
    def fecha_canon(self) -> str:
        """Nombre canónico de fecha de solicitud (fecha pedida)."""
        return self.fecha_pedida

    @property
    def fecha(self) -> str:
        """Alias de compatibilidad para consumidores legacy con claves heterogéneas."""
        return _FechaAlias(self.fecha_pedida, self.fecha_solicitud)

    @property
    def minutos(self) -> int:
        """Duración normalizada a minutos para consumo en UI/reporting."""
        return int(round(self.horas * 60))


@dataclass(frozen=True)
class ConflictoDiaDTO:
    ok: bool
    ids_existentes: list[int]
    accion_sugerida: Optional[str]


@dataclass(frozen=True)
class GrupoConfigDTO:
    id: Optional[int]
    nombre_grupo: Optional[str]
    bolsa_anual_grupo_min: int
    pdf_logo_path: str
    pdf_intro_text: str
    pdf_include_hours_in_horario: Optional[bool] = None


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


@dataclass(frozen=True)
class ResumenIndividualDTO:
    consumidas_periodo_min: int
    bolsa_periodo_min: int
    restantes_periodo_min: int
    consumidas_anual_min: int
    bolsa_anual_min: int
    restantes_anual_min: int


@dataclass(frozen=True)
class ResumenGlobalAnualDTO:
    consumidas_anual_min: int
    bolsa_anual_min: int
    restantes_anual_min: int


@dataclass(frozen=True)
class ResumenGrupoAnualDTO:
    consumidas_anual_min: int
    bolsa_anual_grupo_min: int
    restantes_anual_grupo_min: int


@dataclass(frozen=True)
class ResumenSaldosDTO:
    individual: ResumenIndividualDTO
    global_anual: ResumenGlobalAnualDTO
    grupo_anual: ResumenGrupoAnualDTO


@dataclass(frozen=True)
class ResultadoCrearSolicitudDTO:
    success: bool
    warnings: list[str]
    errores: list[str]
    entidad: SolicitudDTO | None
    saldos: SaldosDTO | None = None
