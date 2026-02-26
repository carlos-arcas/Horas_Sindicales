from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.application.dto import PeriodoFiltro, SaldosDTO, SolicitudDTO
from app.domain.models import Persona, Solicitud
from app.domain.ports import SolicitudRepository
from app.domain.request_time import compute_request_minutes
from app.domain.services import BusinessRuleError
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm


def hours_to_minutes(horas: float) -> int:
    return int(round(horas * 60))


def _total_cuadrante_min(persona: Persona, dia_prefix: str) -> int:
    man = getattr(persona, f"{dia_prefix}_man_min")
    tar = getattr(persona, f"{dia_prefix}_tar_min")
    return man + tar


def _parse_year_month(fecha: str) -> tuple[int, int]:
    parsed = datetime.strptime(fecha, "%Y-%m-%d")
    return parsed.year, parsed.month


def normalize_date(value: str) -> str:
    value_norm = value.strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(value_norm, pattern)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise BusinessRuleError("Fecha inválida para deduplicación.")


def normalize_time(value: str) -> str:
    return minutes_to_hhmm(parse_hhmm(value.strip()))


def _build_periodo_filtro(year: int, month: int | None) -> PeriodoFiltro:
    return PeriodoFiltro.anual(year) if month is None else PeriodoFiltro.mensual(year, month)


def _derived_interval_for_key(dto: SolicitudDTO, persona: Persona) -> tuple[str, str]:
    if dto.completo:
        total_dia = total_cuadrante_por_fecha(persona, normalize_date(dto.fecha_pedida))
        return "00:00", minutes_to_hhmm(total_dia)
    if not dto.desde or not dto.hasta:
        raise BusinessRuleError("Desde y hasta son obligatorios para solicitudes parciales.")
    return normalize_time(dto.desde), normalize_time(dto.hasta)


def solicitud_key(
    dto: SolicitudDTO,
    *,
    persona: Persona,
    delegada_uuid: str,
) -> tuple[object, ...]:
    fecha = normalize_date(dto.fecha_pedida)
    desde, hasta = _derived_interval_for_key(dto, persona)
    return (delegada_uuid, fecha, bool(dto.completo), desde, hasta)


def total_cuadrante_por_fecha(persona: Persona, fecha: str) -> int:
    """Obtiene el total de minutos de cuadrante para la fecha solicitada.

    Si la persona no trabaja fines de semana, sábado y domingo se fuerzan a
    cero para respetar la política de consumo por jornada laborable.
    """
    weekday = datetime.strptime(fecha, "%Y-%m-%d").weekday()
    dia_map = {
        0: "cuad_lun",
        1: "cuad_mar",
        2: "cuad_mie",
        3: "cuad_jue",
        4: "cuad_vie",
        5: "cuad_sab",
        6: "cuad_dom",
    }
    dia_prefix = dia_map[weekday]
    if weekday >= 5 and not persona.trabaja_finde:
        return 0
    return _total_cuadrante_min(persona, dia_prefix)


def _calcular_minutos(dto: SolicitudDTO, persona: Persona | None) -> int:
    """Resuelve minutos finales priorizando entradas explícitas cuando existen.

    Mantiene compatibilidad con formularios que envían horas manuales, pero en
    solicitudes completas usa el cuadrante diario para preservar reglas de negocio
    aunque cambie la interfaz de captura.
    """
    if dto.horas < 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    minutos_manual = hours_to_minutes(dto.horas) if dto.horas > 0 else 0

    if dto.completo:
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total_dia = total_cuadrante_por_fecha(persona, dto.fecha_pedida)
        minutos_calculados = compute_request_minutes(
            dto.desde,
            dto.hasta,
            dto.completo,
            cuadrante_base=total_dia,
        )
        return minutos_manual if minutos_manual > 0 else minutos_calculados

    minutos_calculados = compute_request_minutes(dto.desde, dto.hasta, dto.completo)
    return minutos_manual if minutos_manual > 0 else minutos_calculados


def _calcular_saldos(
    persona: Persona,
    solicitudes_mes: Iterable[Solicitud],
    solicitudes_ano: Iterable[Solicitud],
) -> SaldosDTO:
    consumidas_mes = sum(s.horas_solicitadas_min for s in solicitudes_mes)
    consumidas_ano = sum(s.horas_solicitadas_min for s in solicitudes_ano)
    restantes_mes = persona.horas_mes_min - consumidas_mes
    restantes_ano = persona.horas_ano_min - consumidas_ano
    exceso_mes = abs(restantes_mes) if restantes_mes < 0 else 0
    exceso_ano = abs(restantes_ano) if restantes_ano < 0 else 0
    return SaldosDTO(
        consumidas_mes=consumidas_mes,
        restantes_mes=restantes_mes,
        consumidas_ano=consumidas_ano,
        restantes_ano=restantes_ano,
        exceso_mes=exceso_mes,
        exceso_ano=exceso_ano,
        excedido_mes=exceso_mes > 0,
        excedido_ano=exceso_ano > 0,
    )


def _hash_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _actualizar_pdf_en_repo(
    repo: SolicitudRepository, solicitud: SolicitudDTO, pdf_path: Path, pdf_hash: str | None
) -> SolicitudDTO:
    if solicitud.id is None:
        return solicitud
    repo.update_pdf_info(solicitud.id, str(pdf_path), pdf_hash)
    return replace(solicitud, pdf_path=str(pdf_path), pdf_hash=pdf_hash)


def _solapa_rango(inicio_a: int, fin_a: int, inicio_b: int, fin_b: int) -> bool:
    return inicio_a < fin_b and inicio_b < fin_a
