from __future__ import annotations

from pathlib import Path

import pytest

from app.application.use_cases.solicitudes.servicio_preverificacion_pdf import (
    EntradaNombrePdf,
    ServicioPreverificacionPdf,
)
from app.application.use_cases.solicitudes.use_case import SolicitudUseCases
from app.domain.services import BusinessRuleError


class FakeSistemaArchivos:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self._existentes = existentes or set()

    def existe(self, ruta: Path) -> bool:
        return str(ruta.resolve(strict=False)) in self._existentes


class FakeGeneradorPdf:
    def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
        _ = fechas
        return f"Solicitud {nombre}.pdf"


def test_preverificar_ruta_ok_sin_colision(tmp_path: Path) -> None:
    servicio = ServicioPreverificacionPdf(
        fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorPdf()
    )

    destino = tmp_path / "ok.pdf"
    resultado = servicio.preverificar_ruta(str(destino))

    assert resultado.ruta_destino == str(destino.resolve(strict=False))
    assert resultado.colision is False
    assert resultado.ruta_sugerida is None


def test_preverificar_ruta_colision_simple_sugiere_1(tmp_path: Path) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {str(destino.resolve(strict=False))}
    servicio = ServicioPreverificacionPdf(
        fs=FakeSistemaArchivos(existentes), generador_pdf=FakeGeneradorPdf()
    )

    resultado = servicio.preverificar_ruta(str(destino))

    assert resultado.colision is True
    assert resultado.ruta_sugerida == str(
        (tmp_path / "colision(1).pdf").resolve(strict=False)
    )


def test_preverificar_ruta_colision_multiple_sugiere_n(tmp_path: Path) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {str(destino.resolve(strict=False))}
    existentes.update(
        str((tmp_path / f"colision({indice}).pdf").resolve(strict=False))
        for indice in range(1, 4)
    )
    servicio = ServicioPreverificacionPdf(
        fs=FakeSistemaArchivos(existentes), generador_pdf=FakeGeneradorPdf()
    )

    resultado = servicio.preverificar_ruta(str(destino))

    assert resultado.colision is True
    assert resultado.ruta_sugerida == str(
        (tmp_path / "colision(4).pdf").resolve(strict=False)
    )


def test_preverificar_ruta_limite_sin_sugerencia(tmp_path: Path) -> None:
    destino = tmp_path / "tope.pdf"
    existentes = {str(destino.resolve(strict=False))}
    existentes.update(
        str((tmp_path / f"tope({indice}).pdf").resolve(strict=False))
        for indice in range(1, 4)
    )
    servicio = ServicioPreverificacionPdf(
        fs=FakeSistemaArchivos(existentes), generador_pdf=FakeGeneradorPdf()
    )

    sugerencia = servicio.proponer_ruta_alternativa(str(destino), limite=3)

    assert sugerencia is None
    resultado = servicio.preverificar_ruta(str(destino))
    assert resultado.colision is True


def test_construir_nombre_pdf_normaliza_y_aplica_prefijo() -> None:
    class FakeGeneradorPdfRaro:
        def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
            _ = fechas
            return f"Solicitud: {nombre} / 2025*?.pdf"

    servicio = ServicioPreverificacionPdf(
        fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorPdfRaro()
    )

    nombre = servicio.construir_nombre_pdf(
        EntradaNombrePdf(
            nombre_persona="Ana / Gómez",
            rango=("2025-02-01",),
            prefijo="A Coordinación",
        )
    )

    assert nombre == "A_Coordinación_Solicitud__Ana___Gómez___2025_.pdf"


def test_construir_nombre_pdf_falla_sin_generador() -> None:
    servicio = ServicioPreverificacionPdf(fs=FakeSistemaArchivos(), generador_pdf=None)

    with pytest.raises(ValueError, match="No hay generador PDF configurado"):
        servicio.construir_nombre_pdf(
            EntradaNombrePdf(nombre_persona="Ana", rango=("2025-01-01",))
        )


def test_use_case_colision_pdf_resuelve_ruta_alternativa_sin_io_real(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "colision (1).pdf").resolve(strict=False)),
    }

    use_case = SolicitudUseCases(
        repo=object(),
        persona_repo=object(),
        generador_pdf=FakeGeneradorPdf(),
        fs=FakeSistemaArchivos(existentes),
    )

    resolucion = use_case.resolver_destino_pdf(
        destino, overwrite=False, auto_rename=True
    )

    assert resolucion.colision_detectada is True
    assert str(resolucion.ruta_destino).endswith("colision (2).pdf")


def test_use_case_resolver_destino_pdf_no_lanza_business_rule_error_por_colision(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {str(destino.resolve(strict=False))}
    use_case = SolicitudUseCases(
        repo=object(),
        persona_repo=object(),
        generador_pdf=FakeGeneradorPdf(),
        fs=FakeSistemaArchivos(existentes),
    )

    try:
        resolucion = use_case.resolver_destino_pdf(
            destino, overwrite=False, auto_rename=True
        )
    except BusinessRuleError as exc:  # pragma: no cover - contrato explícito
        pytest.fail(f"No debe elevar BusinessRuleError por colisión: {exc}")

    assert resolucion.colision_detectada is True
    assert str(resolucion.ruta_destino).endswith("colision (1).pdf")
