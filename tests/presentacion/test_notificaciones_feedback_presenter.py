from __future__ import annotations

from app.ui.presentador_feedback_notificaciones import (
    construir_payload_toast_operacion,
    resolver_estado_confirmacion,
)
from app.ui.notification_service import OperationFeedback


def _feedback(status: str) -> OperationFeedback:
    return OperationFeedback(
        title="resultado",
        happened="Se procesaron solicitudes",
        affected_count=2,
        incidents="Sin incidencias",
        next_step="Revisar histórico",
        status=status,
        timestamp="2026-03-10 10:00:00",
        result_id="OP-0001",
        details=["error_tecnico=stacktrace", "correlation_id=CID-1"],
    )


def test_payload_visible_humano_y_detalles_en_capa_secundaria() -> None:
    payload = construir_payload_toast_operacion(_feedback("error"))

    assert payload.level == "error"
    assert "Ha ido mal" in payload.message
    assert "stacktrace" not in payload.message
    assert any("stacktrace" in linea for linea in payload.details)


def test_resolver_estado_confirmacion_prioriza_errores_y_parciales() -> None:
    assert resolver_estado_confirmacion(count=0, errores=[]) == "error"
    assert resolver_estado_confirmacion(count=2, errores=["x"]) == "partial"
    assert resolver_estado_confirmacion(count=2, errores=[]) == "success"
