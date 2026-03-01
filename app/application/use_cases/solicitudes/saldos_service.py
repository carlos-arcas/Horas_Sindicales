from __future__ import annotations

from app.application.dto import (
    PeriodoFiltro,
    ResumenGlobalAnualDTO,
    ResumenGrupoAnualDTO,
    ResumenIndividualDTO,
    ResumenSaldosDTO,
    TotalesGlobalesDTO,
)
from app.domain.models import Persona

MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


def _validar_modo_periodo(filtro: PeriodoFiltro) -> None:
    if filtro.modo not in {"MENSUAL", "ANUAL"}:
        raise ValueError(f"Modo de periodo no soportado: {filtro.modo}")


def sugerir_nombre_pdf_historico(filtro: PeriodoFiltro) -> str:
    _validar_modo_periodo(filtro)
    if filtro.modo == "ANUAL":
        return f"Historico_Horas_Sindicales_(AÑO {filtro.year}).pdf"
    month_name = MONTH_NAMES.get(filtro.month or 0, "")
    return f"Historico_Horas_Sindicales_({month_name} {filtro.year}).pdf"


def calcular_totales_globales(
    *,
    filtro: PeriodoFiltro,
    personas: list[Persona],
    consumidas_por_persona: list[int],
) -> TotalesGlobalesDTO:
    _validar_modo_periodo(filtro)
    total_bolsa = sum(
        persona.horas_mes_min if filtro.modo == "MENSUAL" else persona.horas_ano_min
        for persona in personas
    )
    total_consumidas = sum(consumidas_por_persona)
    return TotalesGlobalesDTO(
        total_consumidas_min=total_consumidas,
        total_bolsa_min=total_bolsa,
        total_restantes_min=total_bolsa - total_consumidas,
    )


def sumar_consumo_solicitudes(solicitudes_min: list[int]) -> int:
    return sum(solicitudes_min)


def acumular_consumo_anual_por_personas(
    *,
    personas: list[Persona],
    consumo_anual_por_persona_min: list[int],
) -> tuple[int, int]:
    return sum(persona.horas_ano_min for persona in personas), sum(consumo_anual_por_persona_min)


def construir_resumen_saldos(
    *,
    persona: Persona,
    filtro: PeriodoFiltro,
    consumidas_periodo_min: int,
    consumidas_anual_persona_min: int,
    total_bolsa_anual_min: int,
    total_consumidas_anual_min: int,
    bolsa_anual_grupo_min: int,
) -> ResumenSaldosDTO:
    _validar_modo_periodo(filtro)
    bolsa_periodo = persona.horas_mes_min if filtro.modo == "MENSUAL" else persona.horas_ano_min
    bolsa_anual = persona.horas_ano_min
    individual = ResumenIndividualDTO(
        consumidas_periodo_min=consumidas_periodo_min,
        bolsa_periodo_min=bolsa_periodo,
        restantes_periodo_min=bolsa_periodo - consumidas_periodo_min,
        consumidas_anual_min=consumidas_anual_persona_min,
        bolsa_anual_min=bolsa_anual,
        restantes_anual_min=bolsa_anual - consumidas_anual_persona_min,
    )
    global_anual = ResumenGlobalAnualDTO(
        consumidas_anual_min=total_consumidas_anual_min,
        bolsa_anual_min=total_bolsa_anual_min,
        restantes_anual_min=total_bolsa_anual_min - total_consumidas_anual_min,
    )
    grupo_anual = ResumenGrupoAnualDTO(
        consumidas_anual_min=total_consumidas_anual_min,
        bolsa_anual_grupo_min=bolsa_anual_grupo_min,
        restantes_anual_grupo_min=bolsa_anual_grupo_min - total_consumidas_anual_min,
    )
    return ResumenSaldosDTO(
        individual=individual,
        global_anual=global_anual,
        grupo_anual=grupo_anual,
    )
