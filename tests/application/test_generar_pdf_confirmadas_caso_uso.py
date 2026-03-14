from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.generar_pdf_confirmadas_caso_uso import (
    GenerarPdfSolicitudesConfirmadasCasoUso,
)


class RepoDummy:
    pass


class PersonaRepoDummy:
    pass


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


def test_genera_pdf_confirmadas_devuelve_contrato_ok(monkeypatch) -> None:
    caso_uso = GenerarPdfSolicitudesConfirmadasCasoUso(
        repo=RepoDummy(),
        persona_repo=PersonaRepoDummy(),
    )

    def _fake_orquestador(*, creadas, destino, **kwargs):
        assert [item.id for item in creadas] == [1, 2]
        assert destino == Path("/tmp/confirmadas.pdf")
        return destino, creadas

    monkeypatch.setattr(
        "app.application.use_cases.confirmacion_pdf.generar_pdf_confirmadas_caso_uso.generar_pdf_confirmadas_orquestado",
        _fake_orquestador,
    )

    ruta, confirmadas_ids, resumen = caso_uso.generar_pdf_confirmadas(
        [_solicitud(1), _solicitud(2)],
        Path("/tmp/confirmadas.pdf"),
        correlation_id="corr-1",
    )

    assert ruta == Path("/tmp/confirmadas.pdf")
    assert confirmadas_ids == [1, 2]
    assert resumen == "OK"


def test_genera_pdf_confirmadas_lista_vacia_controlada() -> None:
    caso_uso = GenerarPdfSolicitudesConfirmadasCasoUso(
        repo=RepoDummy(),
        persona_repo=PersonaRepoDummy(),
    )

    ruta, confirmadas_ids, resumen = caso_uso.generar_pdf_confirmadas(
        [],
        Path("/tmp/confirmadas.pdf"),
    )

    assert ruta is None
    assert confirmadas_ids == []
    assert resumen == "Sin confirmadas para generar PDF."


def test_genera_pdf_confirmadas_sin_ruta_devuelve_error_controlado(monkeypatch) -> None:
    caso_uso = GenerarPdfSolicitudesConfirmadasCasoUso(
        repo=RepoDummy(),
        persona_repo=PersonaRepoDummy(),
    )

    def _fake_orquestador(*, creadas, destino, **kwargs):
        return None, creadas

    monkeypatch.setattr(
        "app.application.use_cases.confirmacion_pdf.generar_pdf_confirmadas_caso_uso.generar_pdf_confirmadas_orquestado",
        _fake_orquestador,
    )

    ruta, confirmadas_ids, resumen = caso_uso.generar_pdf_confirmadas(
        [_solicitud(1)],
        Path("/tmp/confirmadas.pdf"),
    )

    assert ruta is None
    assert confirmadas_ids == []
    assert resumen == "No se generó el PDF."
