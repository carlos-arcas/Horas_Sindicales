from __future__ import annotations

from pathlib import Path

import pytest

from app.application.use_cases.solicitudes.servicio_preflight_pdf import (
    EntradaNombrePdf,
    ServicioPreflightPdf,
)


class FakeSistemaArchivos:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self._existentes = existentes or set()

    def existe(self, ruta: Path) -> bool:
        return str(ruta) in self._existentes


class FakeGeneradorPdf:
    def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
        _ = fechas
        return f"Solicitud {nombre}.pdf"


def test_validar_colision_ok_sin_archivo_existente(tmp_path: Path) -> None:
    servicio = ServicioPreflightPdf(fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorPdf())

    destino = tmp_path / "ok.pdf"
    resultado = servicio.validar_colision(str(destino))

    assert resultado.ruta_destino == str(destino.resolve(strict=False))
    assert resultado.colision is False
    assert resultado.ruta_sugerida is None


def test_validar_colision_propone_ruta_alternativa(tmp_path: Path) -> None:
    destino = tmp_path / "colision.pdf"
    sugerida = tmp_path / "colision(1).pdf"
    fs = FakeSistemaArchivos(existentes={str(destino.resolve(strict=False))})
    servicio = ServicioPreflightPdf(fs=fs, generador_pdf=FakeGeneradorPdf())

    resultado = servicio.validar_colision(str(destino))

    assert resultado.colision is True
    assert resultado.ruta_destino == str(destino.resolve(strict=False))
    assert resultado.ruta_sugerida == str(sugerida)
    assert "Colisión de ruta destino:" in resultado.motivos[0]


def test_construir_nombre_pdf_normaliza_caracteres_raros() -> None:
    class FakeGeneradorPdfRaro:
        def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
            _ = fechas
            return f"Solicitud: {nombre} / 2025*?.pdf"

    servicio = ServicioPreflightPdf(fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorPdfRaro())

    nombre = servicio.construir_nombre_pdf(
        EntradaNombrePdf(nombre_persona="Ana / Gómez", fechas=("2025-02-01",))
    )

    assert nombre == "Solicitud__Ana___Gómez___2025_.pdf"


def test_construir_nombre_pdf_falla_sin_generador() -> None:
    servicio = ServicioPreflightPdf(fs=FakeSistemaArchivos(), generador_pdf=None)

    with pytest.raises(ValueError, match="No hay generador PDF configurado"):
        servicio.construir_nombre_pdf(EntradaNombrePdf(nombre_persona="Ana", fechas=("2025-01-01",)))
