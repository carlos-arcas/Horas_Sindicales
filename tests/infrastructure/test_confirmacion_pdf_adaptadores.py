from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.infrastructure.confirmacion_pdf.adaptadores import (
    GeneradorPdfConfirmadasDesdeCasosUso,
)


class GeneradorPdfConfirmadasEspecificoFake:
    def __init__(self) -> None:
        self.calls = 0

    def generar_pdf_confirmadas(self, confirmadas, destino_pdf, correlation_id=None):
        self.calls += 1
        ids = [sol.id for sol in confirmadas if sol.id is not None]
        return destino_pdf, ids, "OK"


def _solicitud(solicitud_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-02",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
    )


def test_adaptador_pdf_depende_de_pieza_especifica() -> None:
    generador_especifico = GeneradorPdfConfirmadasEspecificoFake()
    adaptador = GeneradorPdfConfirmadasDesdeCasosUso(generador_especifico)

    ruta, ids, resumen = adaptador.generar_pdf_confirmadas(
        [_solicitud(10)],
        Path("/tmp/adaptador.pdf"),
        correlation_id="corr-adaptador",
    )

    assert generador_especifico.calls == 1
    assert ruta == Path("/tmp/adaptador.pdf")
    assert ids == [10]
    assert resumen == "OK"
