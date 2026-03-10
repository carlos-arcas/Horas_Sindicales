from __future__ import annotations

from tests.ui.conftest import require_qt

require_qt()

from app.ui.notification_service import NotificationService, OperationFeedback


class _ToastSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def show(self, message: str, **kwargs: object) -> None:
        self.calls.append({"message": message, **kwargs})


def _feedback(status: str = "success") -> OperationFeedback:
    return OperationFeedback(
        title="Resultado de la operación",
        happened="Se actualizaron 3 solicitudes.",
        affected_count=3,
        incidents="Sin incidencias",
        next_step="Continuar con la revisión",
        status=status,
        timestamp="10/03/2026 09:15:00",
        result_id="OP-0007",
        details=["correlation_id=CID-007", "stack=detalle técnico"],
    )


def test_notify_operation_success_visible_simple_y_detalles_en_segunda_capa() -> None:
    toast = _ToastSpy()
    service = NotificationService(toast=toast, parent=None)  # type: ignore[arg-type]

    service.notify_operation(_feedback("success"))

    assert len(toast.calls) == 1
    call = toast.calls[0]
    assert call["level"] == "success"
    assert "Ha ido bien" in str(call["message"])
    assert "correlation_id" not in str(call["message"])
    assert call.get("action_label") is None
    assert call.get("action_callback") is None
    assert "correlation_id=CID-007" in str(call["details"])


def test_notify_operation_error_visible_simple_y_detalles_en_segunda_capa() -> None:
    toast = _ToastSpy()
    service = NotificationService(toast=toast, parent=None)  # type: ignore[arg-type]

    service.notify_operation(_feedback("error"))

    call = toast.calls[0]
    assert call["level"] == "error"
    assert "Ha ido mal" in str(call["message"])
    assert "stack=detalle técnico" not in str(call["message"])
    assert "stack=detalle técnico" in str(call["details"])


def test_notify_added_pending_muestra_copy_conciso_sin_acciones_extra() -> None:
    from app.application.dto import SolicitudDTO

    toast = _ToastSpy()
    service = NotificationService(toast=toast, parent=None)  # type: ignore[arg-type]

    service.notify_added_pending(
        SolicitudDTO(
            id=7,
            persona_id=10,
            fecha_solicitud="2026-03-10",
            fecha_pedida="2026-03-10",
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones="",
            pdf_path=None,
            pdf_hash=None,
        ),
        on_undo=lambda: None,
    )

    assert len(toast.calls) == 1
    call = toast.calls[0]
    assert call["message"] == "Solicitud agregada a pendientes. OK"
    assert call.get("action_label") is None
    assert call.get("action_callback") is None
