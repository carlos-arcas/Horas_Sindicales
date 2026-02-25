from __future__ import annotations

from app.application.dto import SolicitudDTO


def test_solicitud_dto_expone_alias_fecha_para_compatibilidad_kpi() -> None:
    dto = SolicitudDTO(
        id=1,
        persona_id=99,
        fecha_solicitud="2026-01-10",
        fecha_pedida="2026-01-09",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )

    assert dto.fecha == "2026-01-10"
    assert dto.fecha_canon == "2026-01-10"
