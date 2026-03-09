from __future__ import annotations

import pytest

from app.domain.comunidad_descubrimiento import ErrorLimiteInvalido, ErrorOrdenInvalido, FiltroDescubrimiento


def test_filtro_descubrimiento_normaliza_campos() -> None:
    filtro = FiltroDescubrimiento(orden="recientes", disciplina=" BJJ ", busqueda=" guardia ", limit=10)
    assert filtro.disciplina == "BJJ"
    assert filtro.busqueda == "guardia"


@pytest.mark.parametrize("orden", ["", "aleatorio"])
def test_filtro_descubrimiento_falla_con_orden_invalido(orden: str) -> None:
    with pytest.raises(ErrorOrdenInvalido):
        FiltroDescubrimiento(orden=orden)


def test_filtro_descubrimiento_falla_con_limite_fuera_de_rango() -> None:
    with pytest.raises(ErrorLimiteInvalido):
        FiltroDescubrimiento(limit=0)
