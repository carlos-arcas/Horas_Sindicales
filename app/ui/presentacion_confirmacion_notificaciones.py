from __future__ import annotations

from dataclasses import dataclass

from app.domain.time_utils import minutes_to_hhmm
from app.ui.copy_catalog import copy_text
from app.ui.patterns import status_badge


@dataclass(frozen=True, slots=True)
class PresentacionConfirmacion:
    titulo: str
    color_borde: str
    lineas_resumen: list[str]
    avisos: list[str]


def resolver_titulo_y_borde(status: str) -> tuple[str, str]:
    if status == "success":
        return copy_text("ui.dialogo.confirmada"), "#2a9d8f"
    if status == "partial":
        return copy_text("ui.dialogo.con_avisos"), "#f4a261"
    if status == "error":
        return copy_text("ui.dialogo.error"), "#d62828"
    return copy_text("ui.dialogo.resultado"), "#2a9d8f"


def _resolver_badge(status: str) -> str:
    if status == "success":
        return status_badge("CONFIRMED")
    if status == "partial":
        return status_badge("WARNING")
    return status_badge("ERROR")


def construir_presentacion_confirmacion(
    *,
    status: str,
    count: int,
    total_minutes: int,
    delegadas: list[str],
    saldo_disponible: str,
    timestamp: str,
    result_id: str,
    correlation_id: str | None,
    errores: list[str],
) -> PresentacionConfirmacion:
    titulo, color_borde = resolver_titulo_y_borde(status)
    lineas_resumen = [
        f"{copy_text('ui.notificacion.estado')} {_resolver_badge(status)}",
        f"{copy_text('ui.notificacion.solicitudes_confirmadas')} {count}",
        f"{copy_text('ui.notificacion.delegadas')} {', '.join(delegadas) if delegadas else copy_text('ui.notificacion.sin_delegadas')}",
        f"{copy_text('ui.notificacion.horas_confirmadas')} {minutes_to_hhmm(total_minutes)}",
        f"{copy_text('ui.notificacion.saldo_disponible')} {saldo_disponible}",
        f"{copy_text('ui.notificacion.confirmado')} {timestamp}",
        f"{copy_text('ui.notificacion.referencia')} {result_id}",
        f"{copy_text('ui.notificacion.id_incidente')} {correlation_id or copy_text('ui.toast.no_disponible')}",
    ]
    return PresentacionConfirmacion(
        titulo=titulo,
        color_borde=color_borde,
        lineas_resumen=lineas_resumen,
        avisos=errores[:3],
    )


__all__ = [
    PresentacionConfirmacion.__name__,
    resolver_titulo_y_borde.__name__,
    construir_presentacion_confirmacion.__name__,
]
