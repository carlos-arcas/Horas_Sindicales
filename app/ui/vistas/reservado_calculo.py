from __future__ import annotations

from datetime import date
from typing import Callable, Iterable, Protocol


class SolicitudPeriodo(Protocol):
    fecha_pedida: str


def calcular_minutos_reservados_periodo(
    *,
    persona_id: int,
    pendientes: Iterable[SolicitudPeriodo],
    year: int,
    month: int | None,
    sumar_pendientes_min: Callable[[int, list[SolicitudPeriodo]], int],
) -> int:
    pendientes_filtrados: list[SolicitudPeriodo] = []
    for solicitud in pendientes:
        fecha = date.fromisoformat(solicitud.fecha_pedida)
        if fecha.year != year:
            continue
        if month is not None and fecha.month != month:
            continue
        pendientes_filtrados.append(solicitud)

    if not pendientes_filtrados:
        return 0
    return sumar_pendientes_min(persona_id, pendientes_filtrados)
