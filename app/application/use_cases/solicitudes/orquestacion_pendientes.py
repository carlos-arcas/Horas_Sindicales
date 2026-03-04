from __future__ import annotations

import logging

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.helpers_puros import (
    mensaje_conflicto,
    mensaje_duplicado,
    mensaje_persona_invalida,
    mensaje_warning_saldo_insuficiente,
    normalizar_dto_para_creacion,
    saldo_insuficiente,
)
from app.application.use_cases.solicitudes.validacion_service import (
    calcular_minutos,
    normalize_date,
    parse_year_month,
    solicitud_key,
)
from app.domain.models import ConflictoSolicitud, Persona
from app.domain.ports import SolicitudRepository
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_range import normalize_range, overlaps
from app.domain.time_utils import parse_hhmm


def listar_pendientes_por_persona(repo: SolicitudRepository, persona_id: int, *, solicitud_to_dto) -> list[SolicitudDTO]:
    return [solicitud_to_dto(solicitud) for solicitud in repo.list_pendientes_by_persona(persona_id)]


def listar_pendientes_all(repo: SolicitudRepository, *, solicitud_to_dto) -> list[SolicitudDTO]:
    return [solicitud_to_dto(solicitud) for solicitud in repo.list_pendientes_all()]


def listar_pendientes_huerfanas(repo: SolicitudRepository, *, solicitud_to_dto) -> list[SolicitudDTO]:
    return [solicitud_to_dto(solicitud) for solicitud in repo.list_pendientes_huerfanas()]


def resolver_dto_y_persona_para_creacion(dto: SolicitudDTO, *, persona_repo, validar_solicitud_dto, validar_conflicto_dia, buscar_duplicado) -> tuple[SolicitudDTO, Persona]:
    mensaje_error = mensaje_persona_invalida(dto.persona_id)
    if mensaje_error is not None:
        raise BusinessRuleError(mensaje_error)
    validar_solicitud_dto(dto)
    persona = persona_repo.get_by_id(dto.persona_id)
    if persona is None:
        raise BusinessRuleError("Persona no encontrada.")

    dto_normalizado = normalizar_dto_para_creacion(dto)
    conflicto = validar_conflicto_dia(dto_normalizado.persona_id, dto_normalizado.fecha_pedida, dto_normalizado.completo)
    if not conflicto.ok:
        raise BusinessRuleError(mensaje_conflicto(conflicto.accion_sugerida))
    duplicate = buscar_duplicado(dto_normalizado)
    if duplicate is not None:
        raise BusinessRuleError(mensaje_duplicado(duplicate.generated))
    return dto_normalizado, persona


def agregar_warning_saldo_si_aplica(
    dto: SolicitudDTO,
    *,
    persona: Persona,
    warnings: list[str],
    calcular_saldos,
    logger: logging.Logger,
) -> None:
    minutos = calcular_minutos(dto, persona)
    year, month = parse_year_month(dto.fecha_pedida)
    saldos_previos = calcular_saldos(dto.persona_id, year, month)
    if not saldo_insuficiente(saldos_previos.restantes_mes, saldos_previos.restantes_ano, minutos):
        return
    warning_msg = mensaje_warning_saldo_insuficiente()
    warnings.append(warning_msg)
    logger.warning(
        warning_msg,
        extra={
            "extra": {
                "operation": "crear_solicitud",
                "persona_id": dto.persona_id,
                "fecha_pedida": dto.fecha_pedida,
                "minutos_solicitados": minutos,
                "restantes_mes": saldos_previos.restantes_mes,
                "restantes_ano": saldos_previos.restantes_ano,
            }
        },
    )


def delegada_uuid(persona_id: int, *, persona_repo) -> str:
    resultado = persona_repo.get_or_create_uuid(persona_id)
    if not resultado:
        raise BusinessRuleError("No se pudo resolver el uuid de la delegada.")
    return resultado


def buscar_conflicto_pendiente(
    dto: SolicitudDTO,
    *,
    persona_repo,
    repo,
    excluir_solicitud_id: int | None = None,
) -> ConflictoSolicitud | None:
    persona = persona_repo.get_by_id(dto.persona_id)
    if persona is None:
        raise BusinessRuleError("Persona no encontrada.")
    _, fecha, completo, desde, hasta = solicitud_key(
        dto,
        persona=persona,
        delegada_uuid=delegada_uuid(dto.persona_id, persona_repo=persona_repo),
    )
    desde_min = None if completo else parse_hhmm(str(desde))
    hasta_min = None if completo else parse_hhmm(str(hasta))
    return repo.detectar_conflicto_pendiente(
        dto.persona_id,
        str(fecha),
        desde_min,
        hasta_min,
        completo,
        excluir_solicitud_id=excluir_solicitud_id,
    )


def buscar_duplicado(dto: SolicitudDTO, *, persona_repo, repo, solicitud_to_dto) -> SolicitudDTO | None:
    persona = persona_repo.get_by_id(dto.persona_id)
    if persona is None:
        raise BusinessRuleError("Persona no encontrada.")
    _, fecha, completo, desde, hasta = solicitud_key(
        dto,
        persona=persona,
        delegada_uuid=delegada_uuid(dto.persona_id, persona_repo=persona_repo),
    )
    desde_min = None if completo else parse_hhmm(str(desde))
    hasta_min = None if completo else parse_hhmm(str(hasta))
    duplicate = repo.find_duplicate(dto.persona_id, str(fecha), desde_min, hasta_min, completo)
    if duplicate is None:
        return None
    return solicitud_to_dto(duplicate)


def buscar_similares(dto: SolicitudDTO, *, repo, solicitud_to_dto) -> list[SolicitudDTO]:
    if dto.persona_id <= 0:
        return []
    fecha = normalize_date(dto.fecha_pedida)
    existentes = list(repo.list_by_persona_and_fecha(dto.persona_id, fecha))
    if not existentes:
        return []

    nuevo_inicio, nuevo_fin = normalize_range(completo=dto.completo, desde=dto.desde, hasta=dto.hasta)
    similares: list[SolicitudDTO] = []
    for existente in existentes:
        try:
            existente_inicio, existente_fin = normalize_range(
                completo=existente.completo,
                desde_min=existente.desde_min,
                hasta_min=existente.hasta_min,
            )
        except ValidacionError:
            continue
        if overlaps(nuevo_inicio, nuevo_fin, existente_inicio, existente_fin):
            similares.append(solicitud_to_dto(existente))
    return similares
