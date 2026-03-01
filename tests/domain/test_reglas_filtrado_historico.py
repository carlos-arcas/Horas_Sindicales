from __future__ import annotations

from datetime import date

from app.domain.services import (
    EntradaFiltroHistorico,
    RegistroHistoricoAplicacion,
    decidir_aceptacion,
)


def _entrada(**overrides: object) -> EntradaFiltroHistorico:
    base: dict[str, object] = {
        "patron_busqueda": "",
        "modo_anio": None,
        "anio": None,
        "mes": None,
        "fecha_desde": None,
        "fecha_hasta": None,
        "codigo_estado": None,
        "id_delegada": None,
        "ver_todas": True,
    }
    base.update(overrides)
    return EntradaFiltroHistorico(**base)


def test_decidir_aceptacion_filtra_por_estado() -> None:
    entrada = _entrada(codigo_estado="CONFIRMADA")
    fila = RegistroHistoricoAplicacion(id_persona=1, fecha=date(2025, 1, 7), codigo_estado="PENDIENTE", texto_busqueda="texto")

    decision = decidir_aceptacion(entrada, fila)

    assert decision.acepta is False
    assert decision.codigo_razon == "estado_mismatch"


def test_decidir_aceptacion_sin_filtros_acepta() -> None:
    entrada = _entrada()
    fila = RegistroHistoricoAplicacion(id_persona=4, fecha=None, codigo_estado="PENDIENTE", texto_busqueda="algo")

    decision = decidir_aceptacion(entrada, fila)

    assert decision.acepta is True
    assert decision.codigo_razon == "no_filters"
