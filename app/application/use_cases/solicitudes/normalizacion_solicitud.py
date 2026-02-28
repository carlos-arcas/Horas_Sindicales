from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validacion_service import normalize_date
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm


@dataclass(frozen=True)
class SolicitudNormalizada:
    persona_id: int
    fecha: str
    desde: str
    hasta: str
    tipo: str
    completo: bool
    minutos: int


def normalizar_solicitud(dto: SolicitudDTO) -> SolicitudNormalizada:
    fecha = normalize_date(dto.fecha_pedida)
    if dto.completo:
        return SolicitudNormalizada(
            persona_id=int(dto.persona_id),
            fecha=fecha,
            desde="COMPLETO",
            hasta="COMPLETO",
            tipo="COMPLETO",
            completo=True,
            minutos=_minutos_desde_horas(dto.horas),
        )

    desde = minutes_to_hhmm(parse_hhmm(str(dto.desde or "")))
    hasta = minutes_to_hhmm(parse_hhmm(str(dto.hasta or "")))
    return SolicitudNormalizada(
        persona_id=int(dto.persona_id),
        fecha=fecha,
        desde=desde,
        hasta=hasta,
        tipo="PARCIAL",
        completo=False,
        minutos=_minutos_intervalo(desde, hasta, dto.horas),
    )


def _minutos_desde_horas(horas: float) -> int:
    return int(round(max(horas, 0.0) * 60))


def _minutos_intervalo(desde: str, hasta: str, horas: float) -> int:
    minutos_horas = _minutos_desde_horas(horas)
    if minutos_horas > 0:
        return minutos_horas
    inicio = parse_hhmm(desde)
    fin = parse_hhmm(hasta)
    return max(fin - inicio, 0)
