from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.ui.copy_catalog import copy_text
if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO
    from app.ui.notification_service import ConfirmationSummaryPayload


def sum_solicitudes_minutes(solicitudes: list[SolicitudDTO]) -> int:
    return sum(int(round(solicitud.horas * 60)) for solicitud in solicitudes)


def build_confirmacion_status(creadas: list[SolicitudDTO], errores: list[str]) -> str:
    if not creadas:
        return "error"
    if errores:
        return "partial"
    return "success"


def build_delegadas_confirmadas(creadas: list[SolicitudDTO], persona_nombres: dict[int, str]) -> list[str]:
    return sorted({persona_nombres.get(s.persona_id, f"ID {s.persona_id}") for s in creadas})


def build_confirmation_payload(
    *,
    creadas: list[SolicitudDTO],
    errores: list[str],
    persona_nombres: dict[int, str],
    saldo_disponible: str,
    correlation_id: str | None,
    on_view_history: object,
    on_sync_now: object,
    on_return_to_operativa: object,
    on_undo: object,
) -> "ConfirmationSummaryPayload":
    from app.ui.notification_service import ConfirmationSummaryPayload

    undo_ids = [solicitud.id for solicitud in creadas if solicitud.id is not None]
    return ConfirmationSummaryPayload(
        count=len(creadas),
        total_minutes=sum_solicitudes_minutes(creadas),
        delegadas=build_delegadas_confirmadas(creadas, persona_nombres),
        saldo_disponible=saldo_disponible,
        errores=errores,
        status=build_confirmacion_status(creadas, errores),
        timestamp=datetime.now().strftime(copy_text("ui.formatos.datetime_humano")),
        result_id=(
            f"{copy_text('ui.formatos.prefijo_confirmacion')}"
            f"{datetime.now().strftime(copy_text('ui.formatos.timestamp_corto'))}"
        ),
        correlation_id=correlation_id,
        on_view_history=on_view_history,
        on_sync_now=on_sync_now,
        on_return_to_operativa=on_return_to_operativa,
        undo_seconds=12 if undo_ids else None,
        on_undo=on_undo if undo_ids else None,
    )


def build_confirmation_closure_event(payload: "ConfirmationSummaryPayload", operation_name: str) -> dict[str, object]:
    return {
        "operation": operation_name,
        "result_id": payload.result_id,
        "status": payload.status,
        "count": payload.count,
        "delegadas": payload.delegadas,
        "total_minutes": payload.total_minutes,
        "saldo_disponible": payload.saldo_disponible,
        "errores": payload.errores,
        "timestamp": payload.timestamp,
    }


def build_confirmar_pdf_started_event(selected: list[SolicitudDTO], pdf_path: str) -> dict[str, object]:
    return {
        "count": len(selected),
        "pendientes_ids": [sol.id for sol in selected if sol.id is not None],
        "destino": pdf_path,
    }


def build_confirmar_pdf_finished_event(
    *,
    creadas: list[SolicitudDTO],
    confirmadas_ids: list[int],
    errores: list[str],
    pendientes_restantes_count: int,
    pdf_generado: bool,
) -> dict[str, object]:
    return {
        "creadas": len(creadas),
        "confirmadas_ids": confirmadas_ids,
        "pendientes_restantes": pendientes_restantes_count,
        "errores": len(errores),
        "pdf_generado": pdf_generado,
    }
