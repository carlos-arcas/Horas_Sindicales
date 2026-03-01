from __future__ import annotations

from datetime import datetime

from app.application.dto import FilaReportePdf, ReportePdf, SolicitudDTO, TotalesReportePdf
from app.domain.models import Solicitud
from app.domain.request_time import minutes_to_hours_float
from app.domain.time_utils import horas_decimales_a_minutos, minutes_to_hhmm, parse_hhmm


def minutes_to_hours(minutos: int) -> float:
    return minutes_to_hours_float(minutos)


def hours_to_minutes(horas: float) -> int:
    return horas_decimales_a_minutos(horas)


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


def construir_reporte_pdf(solicitudes: list[SolicitudDTO], nombre_persona: str, genero: str) -> ReportePdf:
    prefijo = "Dª" if genero.upper() == "F" else "D."
    nombre = f"{prefijo} {nombre_persona}"
    filas: list[FilaReportePdf] = []
    for solicitud in sorted(solicitudes, key=lambda item: item.fecha_pedida):
        minutos_fila = max(horas_decimales_a_minutos(solicitud.horas), 0)
        horario = "COMPLETO" if solicitud.completo else f"{solicitud.desde or '--:--'} - {solicitud.hasta or '--:--'}"
        filas.append(
            FilaReportePdf(
                nombre=nombre,
                fecha=datetime.strptime(solicitud.fecha_pedida, "%Y-%m-%d").strftime("%d/%m/%y"),
                horario=horario,
                horas_hhmm=minutes_to_hhmm(minutos_fila),
                minutos_totales_fila=minutos_fila,
            )
        )
    total_minutos = sum(fila.minutos_totales_fila for fila in filas)
    return ReportePdf(
        filas=filas,
        totales=TotalesReportePdf(total_horas_hhmm=minutes_to_hhmm(total_minutos), total_minutos=total_minutos),
    )
