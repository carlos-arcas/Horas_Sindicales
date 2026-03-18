from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.application.use_cases.solicitudes.use_case import SolicitudUseCases
from app.application.use_cases.politica_modo_solo_lectura import crear_politica_modo_solo_lectura

RUTA_SOLICITUDES_USE_CASE = Path("app/application/use_cases/solicitudes/use_case.py")


def test_wiring_correcto_con_fs_obligatorio() -> None:
    fs = Mock()
    use_case = SolicitudUseCases(repo=Mock(), persona_repo=Mock(), fs=fs, politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    assert use_case._fs is fs  # noqa: SLF001 - verificación de wiring interno


def test_solicitud_use_case_falla_temprano_si_falta_fs() -> None:
    with pytest.raises(TypeError, match="fs"):
        SolicitudUseCases(repo=Mock(), persona_repo=Mock(), politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))


def test_use_case_no_define_fallback_fs_implicito() -> None:
    arbol = ast.parse(RUTA_SOLICITUDES_USE_CASE.read_text(encoding="utf-8"))
    clases = {
        nodo.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ClassDef)
    }

    assert "_SistemaArchivosNoConfigurado" not in clases



def test_solicitud_use_case_falla_temprano_si_falta_politica() -> None:
    with pytest.raises(TypeError, match="politica_modo_solo_lectura"):
        SolicitudUseCases(repo=Mock(), persona_repo=Mock(), fs=Mock())


def test_use_case_no_define_fallback_politica_implicito() -> None:
    contenido = RUTA_SOLICITUDES_USE_CASE.read_text(encoding="utf-8")

    assert "politica_modo_solo_lectura: PoliticaModoSoloLectura | None = None" not in contenido
    assert "or crear_politica_modo_solo_lectura()" not in contenido
