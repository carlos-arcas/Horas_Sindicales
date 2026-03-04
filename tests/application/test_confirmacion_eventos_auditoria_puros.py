from __future__ import annotations

from types import SimpleNamespace

from app.ui.vistas.confirmacion_eventos_auditoria import (
    build_confirmar_pdf_finished_event,
    build_confirmar_pdf_started_event,
    build_confirmacion_status,
    build_delegadas_confirmadas,
    sum_solicitudes_minutes,
)


def test_build_confirmacion_status_prioriza_error_y_partial() -> None:
    assert build_confirmacion_status([], ["e"]) == "error"
    assert build_confirmacion_status([SimpleNamespace(horas=1.0)], ["e"]) == "partial"
    assert build_confirmacion_status([SimpleNamespace(horas=1.0)], []) == "success"


def test_build_delegadas_confirmadas_usa_nombre_o_fallback_id() -> None:
    creadas = [SimpleNamespace(persona_id=1), SimpleNamespace(persona_id=2)]

    delegadas = build_delegadas_confirmadas(creadas, {1: "Ana"})

    assert delegadas == ["Ana", "ID 2"]


def test_eventos_confirmacion_pdf_y_minutos() -> None:
    selected = [SimpleNamespace(id=10), SimpleNamespace(id=None)]
    started = build_confirmar_pdf_started_event(selected, "/tmp/reporte.pdf")
    assert started == {"count": 2, "pendientes_ids": [10], "destino": "/tmp/reporte.pdf"}

    creadas = [SimpleNamespace(horas=1.5), SimpleNamespace(horas=0.5)]
    finished = build_confirmar_pdf_finished_event(
        creadas=creadas,
        confirmadas_ids=[10, 11],
        errores=["warning"],
        pendientes_restantes_count=3,
        pdf_generado=True,
    )

    assert sum_solicitudes_minutes(creadas) == 120
    assert finished["creadas"] == 2
    assert finished["errores"] == 1
    assert finished["pdf_generado"] is True
