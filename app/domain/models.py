from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Persona:
    id: Optional[int]
    nombre: str
    genero: str
    horas_mes_min: int
    horas_ano_min: int
    horas_jornada_defecto_min: int
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


@dataclass(frozen=True)
class Solicitud:
    id: Optional[int]
    persona_id: int
    fecha_solicitud: str
    fecha_pedida: str
    desde_min: Optional[int]
    hasta_min: Optional[int]
    completo: bool
    horas_solicitadas_min: int
    observaciones: Optional[str]
    pdf_path: Optional[str]
    pdf_hash: Optional[str]
