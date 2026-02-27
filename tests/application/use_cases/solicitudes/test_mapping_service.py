from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.mapping_service import (
    dto_to_solicitud,
    hours_to_minutes,
    minutes_to_hours,
    solicitud_to_dto,
)
from app.domain.models import Solicitud


def test_minutes_to_hours_convierte_minutos() -> None:
    assert minutes_to_hours(90) == 1.5


@pytest.mark.parametrize("horas,esperado", [(1.5, 90), (0.0, 0), (1.3333, 80)])
def test_hours_to_minutes_redondea(horas: float, esperado: int) -> None:
    assert hours_to_minutes(horas) == esperado


def test_solicitud_to_dto_mapea_rango_y_notas() -> None:
    solicitud = Solicitud(
        id=1,
        persona_id=2,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-02",
        desde_min=540,
        hasta_min=630,
        completo=False,
        horas_solicitadas_min=90,
        observaciones="obs",
        notas="nota",
        pdf_path="/tmp/doc.pdf",
        pdf_hash="hash",
        generated=True,
    )

    dto = solicitud_to_dto(solicitud)

    assert dto.desde == "09:00"
    assert dto.hasta == "10:30"
    assert dto.notas == "nota"
    assert dto.pdf_path == "/tmp/doc.pdf"
    assert dto.generated is True


def test_solicitud_to_dto_fallback_notas_en_observaciones() -> None:
    solicitud = Solicitud(
        id=1,
        persona_id=2,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-02",
        desde_min=None,
        hasta_min=None,
        completo=True,
        horas_solicitadas_min=480,
        observaciones="obs-fallback",
        notas=None,
    )

    dto = solicitud_to_dto(solicitud)

    assert dto.notas == "obs-fallback"
    assert dto.desde is None
    assert dto.hasta is None


def test_dto_to_solicitud_mapea_fecha_canonica_y_rango() -> None:
    dto = SolicitudDTO(
        id=7,
        persona_id=3,
        fecha_solicitud="2025-02-05",
        fecha_pedida="2025-02-08",
        desde="08:00",
        hasta="09:15",
        completo=False,
        horas=1.25,
        observaciones="obs",
        notas="nota",
        pdf_path=None,
        pdf_hash=None,
        generated=False,
    )

    solicitud = dto_to_solicitud(dto)

    assert solicitud.fecha_solicitud == "2025-02-08"
    assert solicitud.desde_min == 480
    assert solicitud.hasta_min == 555
    assert solicitud.horas_solicitadas_min == 75


def test_dto_to_solicitud_fallback_notas_en_observaciones() -> None:
    dto = SolicitudDTO(
        id=None,
        persona_id=3,
        fecha_solicitud="2025-02-05",
        fecha_pedida="2025-02-08",
        desde=None,
        hasta=None,
        completo=True,
        horas=8.0,
        observaciones="obs-fallback",
        notas=None,
        pdf_path="f.pdf",
        pdf_hash="h",
        generated=True,
    )

    solicitud = dto_to_solicitud(dto)

    assert solicitud.notas == "obs-fallback"
    assert solicitud.generated is True
    assert solicitud.pdf_path == "f.pdf"
