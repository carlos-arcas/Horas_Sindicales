from __future__ import annotations

from pathlib import Path

from app.application.use_cases.solicitudes.servicio_preflight_pdf import (
    EntradaNombrePdf,
    ServicioPreflightPdf,
)
from app.application.use_cases.solicitudes.use_case import SolicitudUseCases


class FakeSistemaArchivos:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self._existentes = existentes or set()

    def existe_ruta(self, ruta: Path) -> bool:
        return str(ruta.resolve(strict=False)) in self._existentes

    def existe(self, ruta: Path) -> bool:
        return self.existe_ruta(ruta)


class FakeGeneradorPdf:
    def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
        _ = fechas
        return f"Solicitud {nombre}.pdf"


def test_validar_colision_ok_sin_existencia(tmp_path: Path) -> None:
    servicio = ServicioPreflightPdf(
        fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorPdf()
    )

    destino = tmp_path / "ok.pdf"
    resultado = servicio.validar_colision(str(destino))

    assert resultado.colision is False
    assert resultado.ruta_destino == str(destino.resolve(strict=False))
    assert resultado.ruta_sugerida is None


def test_validar_colision_detecta_existente_y_motivo_con_ruta(tmp_path: Path) -> None:
    destino = tmp_path / "colision.pdf"
    servicio = ServicioPreflightPdf(
        fs=FakeSistemaArchivos({str(destino.resolve(strict=False))}),
        generador_pdf=FakeGeneradorPdf(),
    )

    resultado = servicio.validar_colision(str(destino))

    assert resultado.colision is True
    assert resultado.motivos == (
        f"Colisión de ruta destino: {destino.resolve(strict=False)}",
    )


def test_construir_ruta_destino_normaliza_caracteres_raros() -> None:
    class FakeGeneradorRaro:
        def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
            _ = (nombre, fechas)
            return ' Solicitud: A/B * "?.PDF '

    servicio = ServicioPreflightPdf(
        fs=FakeSistemaArchivos(), generador_pdf=FakeGeneradorRaro()
    )

    ruta = servicio.construir_ruta_destino(
        EntradaNombrePdf(nombre_persona="Ana", fechas=("2026-01-01",)),
        "~/tmp preflight",
    )

    assert ruta.endswith("Solicitud__A_B____.PDF")


def test_sugerir_ruta_alternativa_propone_siguiente_disponible(tmp_path: Path) -> None:
    destino = tmp_path / "solicitud.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "solicitud(1).pdf").resolve(strict=False)),
        str((tmp_path / "solicitud(2).pdf").resolve(strict=False)),
    }
    servicio = ServicioPreflightPdf(
        fs=FakeSistemaArchivos(existentes), generador_pdf=FakeGeneradorPdf()
    )

    sugerida = servicio.sugerir_ruta_alternativa(str(destino))

    assert sugerida == str((tmp_path / "solicitud(3).pdf").resolve(strict=False))


def test_use_case_resuelve_colision_con_renombrado_automatico(tmp_path: Path) -> None:
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

    resolucion = use_case.coordinador_confirmacion_pdf.resolver_destino_pdf(
        destino, overwrite=False, auto_rename=True
    )

    assert resolucion.colision_detectada is True
    assert str(resolucion.ruta_original).endswith("colision.pdf")
    assert str(resolucion.ruta_destino).endswith("colision (2).pdf")
