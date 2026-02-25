from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from app.application.dto import SolicitudDTO


@dataclass(frozen=True)
class PendingInterval:
    index: int
    start_min: int
    end_min: int


def detect_pending_time_conflicts(
    solicitudes: list[SolicitudDTO],
    interval_resolver: Callable[[SolicitudDTO], tuple[int, int]],
) -> set[int]:
    """Devuelve índices de solicitudes pendientes con solapes horarios.

    Una colisión temporal se define por la tupla
    ``(persona_id, fecha_pedida, intervalo_horario)``.
    Por ello, los solapes sólo se evalúan dentro de la misma delegada
    en la misma fecha, nunca entre delegadas distintas.
    """

    grouped: dict[tuple[int, str], list[PendingInterval]] = defaultdict(list)
    for index, solicitud in enumerate(solicitudes):
        start_min, end_min = interval_resolver(solicitud)
        grouped[(solicitud.persona_id, solicitud.fecha_pedida)].append(
            PendingInterval(index=index, start_min=start_min, end_min=end_min)
        )

    conflicts: set[int] = set()
    for intervals in grouped.values():
        ordered = sorted(intervals, key=lambda item: (item.start_min, item.end_min))
        for pos in range(1, len(ordered)):
            prev = ordered[pos - 1]
            current = ordered[pos]
            if current.start_min < prev.end_min:
                conflicts.add(prev.index)
                conflicts.add(current.index)
    return conflicts
