from __future__ import annotations

import pytest

from app.domain.personajes import (
    DescripcionPersonajeInvalida,
    NombrePersonajeInvalido,
    normalizar_nombre_personaje,
    validar_descripcion_personaje,
)


def test_normalizar_nombre_personaje_aplica_trim_y_espacios() -> None:
    assert normalizar_nombre_personaje("  Ana   Luz  ") == "Ana Luz"


def test_normalizar_nombre_personaje_falla_si_vacio() -> None:
    with pytest.raises(NombrePersonajeInvalido):
        normalizar_nombre_personaje("   ")


def test_validar_descripcion_personaje_falla_si_supera_maximo() -> None:
    with pytest.raises(DescripcionPersonajeInvalida):
        validar_descripcion_personaje("x" * 1201)
