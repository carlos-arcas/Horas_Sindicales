from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Persona:
    """Representa a una delegada con su bolsa de horas y patrón de cuadrante.

    El modelo conserva el cuadrante en minutos por tramo para evitar ambigüedades
    de redondeo cuando se convierten horas parciales y para garantizar que todas
    las reglas de saldo operan con una única unidad de cálculo.
    """

    id: Optional[int]
    nombre: str
    genero: str
    horas_mes_min: int
    horas_ano_min: int
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
class Solicitud:
    """Solicitud de horas sindicales lista para validación y persistencia.

    La entidad guarda tanto el intervalo horario (si existe) como los minutos
    resultantes para que la lógica de negocio pueda validar duplicados y saldos
    sin recalcular datos históricos con reglas que podrían evolucionar.
    """

    id: Optional[int]
    persona_id: int
    fecha_solicitud: str
    fecha_pedida: str
    desde_min: Optional[int]
    hasta_min: Optional[int]
    completo: bool
    horas_solicitadas_min: int
    observaciones: Optional[str]
    notas: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_hash: Optional[str] = None
    generated: bool = False


@dataclass(frozen=True)
class GrupoConfig:
    """Configuración global que afecta a cálculos agregados y salida de PDF.

    Se mantiene separada de `Persona` y `Solicitud` porque representa decisiones
    organizativas compartidas por todo el grupo, no atributos de una delegada.
    """

    id: Optional[int]
    nombre_grupo: Optional[str]
    bolsa_anual_grupo_min: int
    pdf_logo_path: str
    pdf_intro_text: str
    pdf_include_hours_in_horario: Optional[bool] = None


@dataclass(frozen=True)
class SheetsConfig:
    spreadsheet_id: str
    credentials_path: str
    device_id: str
