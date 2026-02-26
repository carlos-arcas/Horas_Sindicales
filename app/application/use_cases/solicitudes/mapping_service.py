from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Solicitud
from app.domain.request_time import minutes_to_hours_float
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm


def minutes_to_hours(minutos: int) -> float:
    return minutes_to_hours_float(minutos)


def hours_to_minutes(horas: float) -> int:
    return int(round(horas * 60))


def solicitud_to_dto(solicitud: Solicitud) -> SolicitudDTO:
    desde = minutes_to_hhmm(solicitud.desde_min) if solicitud.desde_min is not None else None
    hasta = minutes_to_hhmm(solicitud.hasta_min) if solicitud.hasta_min is not None else None
    notas = solicitud.notas if solicitud.notas is not None else solicitud.observaciones
    return SolicitudDTO(
        id=solicitud.id,
        persona_id=solicitud.persona_id,
        fecha_solicitud=solicitud.fecha_solicitud,
        fecha_pedida=solicitud.fecha_pedida,
        desde=desde,
        hasta=hasta,
        completo=solicitud.completo,
        horas=minutes_to_hours(solicitud.horas_solicitadas_min),
        observaciones=solicitud.observaciones,
        pdf_path=solicitud.pdf_path,
        pdf_hash=solicitud.pdf_hash,
        notas=notas,
        generated=solicitud.generated,
    )


def dto_to_solicitud(dto: SolicitudDTO) -> Solicitud:
    desde_min = parse_hhmm(dto.desde) if dto.desde else None
    hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
    notas = dto.notas if dto.notas is not None else dto.observaciones
    return Solicitud(
        id=dto.id,
        persona_id=dto.persona_id,
        fecha_solicitud=dto.fecha_canon,
        fecha_pedida=dto.fecha_pedida,
        desde_min=desde_min,
        hasta_min=hasta_min,
        completo=dto.completo,
        horas_solicitadas_min=hours_to_minutes(dto.horas),
        observaciones=dto.observaciones,
        notas=notas,
        pdf_path=dto.pdf_path,
        pdf_hash=dto.pdf_hash,
        generated=dto.generated,
    )
