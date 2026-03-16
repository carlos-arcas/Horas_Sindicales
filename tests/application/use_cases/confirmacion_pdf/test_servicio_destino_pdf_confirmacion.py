from __future__ import annotations

from pathlib import Path

from app.application.use_cases.confirmacion_pdf.servicio_destino_pdf_confirmacion import (
    ServicioDestinoPdfConfirmacion,
)


class FakeSistemaArchivos:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self._existentes = existentes or set()

    def existe(self, ruta: Path) -> bool:
        return str(ruta.resolve(strict=False)) in self._existentes


class FakeGeneradorPdf:
    def construir_nombre_archivo(self, nombre: str, fechas: list[str]) -> str:
        _ = fechas
        return f"Solicitud {nombre}.pdf"


def test_servicio_destino_colision_pdf_resuelve_ruta_alternativa_sin_io_real(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "colision (1).pdf").resolve(strict=False)),
    }

    servicio = ServicioDestinoPdfConfirmacion(
        persona_repo=object(),
        generador_pdf=FakeGeneradorPdf(),
        fs=FakeSistemaArchivos(existentes),
    )

    resolucion = servicio.resolver_destino_pdf(destino, overwrite=False, auto_rename=True)

    assert resolucion.colision_detectada is True
    assert str(resolucion.ruta_destino).endswith("colision (2).pdf")


def test_servicio_destino_resuelve_colision_con_renombrado_automatico(tmp_path: Path) -> None:
    destino = tmp_path / "colision.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "colision (1).pdf").resolve(strict=False)),
    }
    servicio = ServicioDestinoPdfConfirmacion(
        persona_repo=object(),
        generador_pdf=FakeGeneradorPdf(),
        fs=FakeSistemaArchivos(existentes),
    )

    resolucion = servicio.resolver_destino_pdf(
        destino, overwrite=False, auto_rename=True
    )

    assert resolucion.colision_detectada is True
    assert str(resolucion.ruta_original).endswith("colision.pdf")
    assert str(resolucion.ruta_destino).endswith("colision (2).pdf")
