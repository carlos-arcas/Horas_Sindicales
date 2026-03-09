from __future__ import annotations

import pytest

from app.application.comunidad.caso_uso_descubrir import DescubrirComunidadCasoUso
from app.domain.comunidad_descubrimiento import FiltroDescubrimiento


class RepoComunidadFake:
    def __init__(self, fallar: bool = False) -> None:
        self.fallar = fallar

    def listar_publicaciones(self, filtro):
        if self.fallar:
            raise RuntimeError("db_error")
        return []

    def listar_disciplinas_disponibles(self):
        if self.fallar:
            raise RuntimeError("db_error")
        return []

    def listar_perfiles_sugeridos(self, limite: int = 5):
        if self.fallar:
            raise RuntimeError("db_error")
        return []


def test_descubrir_comunidad_devuelve_estado_vacio_sin_error() -> None:
    resultado = DescubrirComunidadCasoUso(RepoComunidadFake()).ejecutar(FiltroDescubrimiento())
    assert resultado.publicaciones == ()
    assert resultado.disciplinas == ()
    assert resultado.perfiles_sugeridos == ()
    assert resultado.pestaña_siguiendo_habilitada is False


def test_descubrir_comunidad_propaga_error_de_infraestructura() -> None:
    caso = DescubrirComunidadCasoUso(RepoComunidadFake(fallar=True))
    with pytest.raises(RuntimeError, match="db_error"):
        caso.ejecutar(FiltroDescubrimiento())
