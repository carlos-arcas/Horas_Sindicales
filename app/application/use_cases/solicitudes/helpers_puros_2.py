from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Solicitud
from app.domain.time_utils import parse_hhmm


def correlation_id_or_new(correlation_id: str | None, generated_id: str) -> str:
    return correlation_id or generated_id


def debe_emitir_evento(correlation_id: str | None) -> bool:
    return bool(correlation_id)


def payload_evento_inicio(dto: SolicitudDTO) -> dict[str, int | str]:
    return {"persona_id": dto.persona_id, "fecha_pedida": dto.fecha_pedida}


def payload_evento_exito(solicitud_id: int | None, persona_id: int) -> dict[str, int | None]:
    return {"solicitud_id": solicitud_id, "persona_id": persona_id}


def rango_en_minutos(desde: str | None, hasta: str | None) -> tuple[int | None, int | None]:
    return (parse_hhmm(desde) if desde else None, parse_hhmm(hasta) if hasta else None)


def notas_para_guardar(notas: str | None, observaciones: str | None) -> str | None:
    return notas if notas is not None else observaciones


def solicitud_desde_dto(
    dto: SolicitudDTO,
    *,
    minutos: int,
    desde_min: int | None,
    hasta_min: int | None,
) -> Solicitud:
    return Solicitud(
        id=None,
        persona_id=dto.persona_id,
        fecha_solicitud=dto.fecha_solicitud,
        fecha_pedida=dto.fecha_pedida,
        desde_min=desde_min,
        hasta_min=hasta_min,
        completo=dto.completo,
        horas_solicitadas_min=minutos,
        observaciones=dto.observaciones,
        notas=notas_para_guardar(dto.notas, dto.observaciones),
        pdf_path=dto.pdf_path,
        pdf_hash=dto.pdf_hash,
    )


def mensaje_duplicado_desde_estado(generated: bool) -> str:
    return "Duplicado confirmado" if generated else "Duplicado pendiente"
