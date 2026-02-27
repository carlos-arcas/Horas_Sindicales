from __future__ import annotations

from app.application.sheets_service import SHEETS_SCHEMA
from app.infrastructure.health_probes import (
    completar_validaciones_pendientes,
    normalizar_headers_fila,
    resultado_sin_configuracion,
    validar_configuracion_basica,
    validar_headers_solicitudes,
    validar_worksheets_existentes,
)


def test_resultado_sin_configuracion() -> None:
    result = resultado_sin_configuracion()
    assert result["credentials"][0] is False
    assert result["worksheet"][0] is False


def test_validar_configuracion_basica_faltante() -> None:
    result = validar_configuracion_basica("", "")
    assert result["credentials"][0] is False
    assert result["spreadsheet"][0] is False


def test_completar_validaciones_pendientes() -> None:
    parcial = validar_configuracion_basica("", "")
    result = completar_validaciones_pendientes(parcial)
    assert result["headers"][1].startswith("No se puede validar")


def test_validar_worksheets_existentes_ok() -> None:
    ok, msg, _ = validar_worksheets_existentes({"delegadas": 1, "solicitudes": 1, "cuadrantes": 1})
    assert ok is True
    assert "esperadas" in msg


def test_validar_worksheets_existentes_faltan() -> None:
    ok, msg, _ = validar_worksheets_existentes({"delegadas": 1})
    assert ok is False
    assert "solicitudes" in msg


def test_normalizar_headers_fila() -> None:
    assert normalizar_headers_fila([[" UUID ", "Fecha"]]) == ["uuid", "fecha"]


def test_normalizar_headers_fila_vacio() -> None:
    assert normalizar_headers_fila([]) == []


def test_validar_headers_solicitudes_ok() -> None:
    ok, _, _ = validar_headers_solicitudes(SHEETS_SCHEMA["solicitudes"])
    assert ok is True


def test_validar_headers_solicitudes_faltantes() -> None:
    ok, msg, _ = validar_headers_solicitudes(["uuid"])
    assert ok is False
    assert "Faltan cabeceras" in msg
