from __future__ import annotations

import pytest

from app.application.dto import PeriodoFiltro
from app.application.use_cases.solicitudes.saldos_service import (
    calcular_totales_globales,
    construir_resumen_saldos,
)
from app.domain.models import Persona


def _persona(persona_id: int, *, horas_mes_min: int, horas_ano_min: int) -> Persona:
    return Persona(
        id=persona_id,
        nombre=f"Delegada {persona_id}",
        genero="F",
        horas_mes_min=horas_mes_min,
        horas_ano_min=horas_ano_min,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_calcular_totales_globales_mensual_ok() -> None:
    personas = [_persona(1, horas_mes_min=300, horas_ano_min=3600), _persona(2, horas_mes_min=200, horas_ano_min=2400)]

    resultado = calcular_totales_globales(
        filtro=PeriodoFiltro.mensual(2025, 1),
        personas=personas,
        consumidas_por_persona=[120, 30],
    )

    assert resultado.total_bolsa_min == 500
    assert resultado.total_consumidas_min == 150
    assert resultado.total_restantes_min == 350


def test_construir_resumen_saldos_permite_saldo_negativo_borde() -> None:
    persona = _persona(1, horas_mes_min=120, horas_ano_min=1200)

    resumen = construir_resumen_saldos(
        persona=persona,
        filtro=PeriodoFiltro.mensual(2025, 2),
        consumidas_periodo_min=180,
        consumidas_anual_persona_min=1320,
        total_bolsa_anual_min=1200,
        total_consumidas_anual_min=1500,
        bolsa_anual_grupo_min=1400,
    )

    assert resumen.individual.restantes_periodo_min == -60
    assert resumen.individual.restantes_anual_min == -120
    assert resumen.grupo_anual.restantes_anual_grupo_min == -100


def test_construir_resumen_saldos_error_si_filtro_invalido() -> None:
    persona = _persona(1, horas_mes_min=120, horas_ano_min=1200)

    with pytest.raises(ValueError, match="Modo de periodo"):
        construir_resumen_saldos(
            persona=persona,
            filtro=PeriodoFiltro(year=2025, month=1, modo="TRIMESTRAL"),
            consumidas_periodo_min=10,
            consumidas_anual_persona_min=20,
            total_bolsa_anual_min=100,
            total_consumidas_anual_min=50,
            bolsa_anual_grupo_min=70,
        )
