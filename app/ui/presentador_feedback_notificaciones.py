from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ui.copy_catalog import copy_text


class FeedbackOperacion(Protocol):
    happened: str
    affected_count: int
    incidents: str
    next_step: str
    status: str
    timestamp: str | None
    result_id: str | None
    details: list[str] | None


@dataclass(frozen=True, slots=True)
class OperationToastPayload:
    message: str
    level: str
    details: list[str]


def mapear_estado_a_nivel_toast(status: str) -> str:
    if status == "error":
        return "error"
    if status == "partial":
        return "warning"
    return "success"


def resolver_estado_humano(status: str) -> str:
    if status == "error":
        return copy_text("ui.toast.estado_error")
    return copy_text("ui.toast.estado_exito")


def resolver_mensaje_humano(status: str) -> str:
    if status == "error":
        return copy_text("ui.toast.operacion_error")
    if status == "partial":
        return copy_text("ui.toast.operacion_con_avisos")
    return copy_text("ui.toast.operacion_ok")


def construir_detalles_feedback(feedback: FeedbackOperacion) -> list[str]:
    detalles = [
        feedback.happened,
        f"{copy_text('ui.toast.solicitudes_afectadas')} {feedback.affected_count}",
        f"{copy_text('ui.toast.incidencias')} {feedback.incidents}",
        f"{copy_text('ui.toast.siguiente_paso')} {feedback.next_step}",
        f"{copy_text('ui.toast.fecha_hora')} {feedback.timestamp}",
        f"{copy_text('ui.toast.identificador')} {feedback.result_id}",
    ]
    if feedback.details:
        detalles.extend(feedback.details)
    return detalles


def construir_payload_toast_operacion(feedback: FeedbackOperacion) -> OperationToastPayload:
    message = (
        f"{copy_text('ui.toast.estado')} {resolver_estado_humano(feedback.status)}\n"
        f"{resolver_mensaje_humano(feedback.status)}"
    )
    return OperationToastPayload(
        message=message,
        level=mapear_estado_a_nivel_toast(feedback.status),
        details=construir_detalles_feedback(feedback),
    )


def resolver_estado_confirmacion(*, count: int, errores: list[str]) -> str:
    if count <= 0:
        return "error"
    if errores:
        return "partial"
    return "success"
