"""Helpers puros para simplificar `SolicitudUseCases`.

Este módulo concentra operaciones de selección, validación y formateo que no
requieren estado interno del caso de uso.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
import time
from typing import Any, Protocol, cast

from app.application.dto import ConflictoDiaDTO, PeriodoFiltro, ResumenSaldosDTO, SolicitudDTO, TotalesGlobalesDTO
from app.application.dtos.contexto_operacion import ContextoOperacion
from app.application.operaciones.exportacion_pdf_historico_operacion import RequestExportacionPdfHistorico
from app.application.pending_conflicts import detect_pending_time_conflicts
from app.domain.models import Persona, Solicitud
from app.domain.request_time import compute_request_minutes
from app.domain.services import BusinessRuleError, ValidacionError
from app.core.errors import InfraError, PersistenceError
from app.domain.time_range import normalize_range


class _ConflictosExportacionPdf(Protocol):
    no_ejecutable: bool
    conflictos: list[str]


class ResultadoExportacionPdfHistorico(Protocol):
    conflictos: _ConflictosExportacionPdf
    artefactos_generados: list[str]

class ErrorAplicacionSolicitud(BusinessRuleError):
    def __init__(self, mensaje: str, *, incident_id: str) -> None:
        super().__init__(f"{mensaje}. ID de incidente: {incident_id}")
        self.incident_id = incident_id


def resolver_correlation_id(correlation_id: str | None, contexto: ContextoOperacion | None) -> str | None:
    if contexto is not None:
        return contexto.correlation_id
    return correlation_id


def construir_conflicto_dia(existentes: Iterable[Solicitud], tipo_nuevo: bool) -> ConflictoDiaDTO:
    solicitudes = list(existentes)
    if tipo_nuevo:
        conflictos = [s for s in solicitudes if not s.completo]
    else:
        conflictos = [s for s in solicitudes if s.completo]
    ids = [s.id for s in conflictos if s.id is not None]
    if not ids:
        return ConflictoDiaDTO(ok=True, ids_existentes=[], accion_sugerida=None)
    return ConflictoDiaDTO(ok=False, ids_existentes=ids, accion_sugerida="sustituir")


def validar_tipo_para_sustitucion(*, es_completa: bool, requiere_completa: bool) -> None:
    if es_completa == requiere_completa:
        return
    tipo_requerido = "completa" if requiere_completa else "parcial"
    raise BusinessRuleError(f"La solicitud debe ser {tipo_requerido} para esta sustitución.")


def ids_para_sustitucion(existentes: Iterable[Solicitud], *, eliminar_completas: bool) -> list[int]:
    return [s.id for s in existentes if s.id is not None and s.completo == eliminar_completas]


def obtener_persona_o_error(persona: Persona | None) -> Persona:
    if persona is None:
        raise BusinessRuleError("Persona no encontrada.")
    return persona


def sugerir_completo_minutos(total_dia: int) -> int:
    return total_dia if total_dia > 0 else 0


def sumar_pendientes_minutos(
    solicitudes: Iterable[SolicitudDTO],
    *,
    calcular_minutos: Callable[[SolicitudDTO], int],
) -> int:
    return sum(calcular_minutos(solicitud) for solicitud in solicitudes)


def detectar_conflictos_pendientes_con_resolutor(
    solicitudes: Iterable[SolicitudDTO],
    *,
    resolver_persona: Callable[[int], Persona],
    total_cuadrante_por_fecha: Callable[[Persona, str], int],
) -> set[int]:
    solicitudes_list = list(solicitudes)
    if not solicitudes_list:
        return set()

    persona_cache: dict[int, Persona] = {}

    def resolve_interval(dto: SolicitudDTO) -> tuple[int, int]:
        persona = persona_cache.get(dto.persona_id)
        if persona is None:
            persona = resolver_persona(dto.persona_id)
            persona_cache[dto.persona_id] = persona

        if dto.completo:
            total_dia = total_cuadrante_por_fecha(persona, dto.fecha_pedida)
            compute_request_minutes(dto.desde, dto.hasta, dto.completo, cuadrante_base=total_dia)
        return normalize_range(completo=dto.completo, desde=dto.desde, hasta=dto.hasta)

    return detect_pending_time_conflicts(solicitudes_list, resolve_interval)


def seleccionar_solicitudes_por_filtro(
    pendientes: Iterable[SolicitudDTO], filtro_delegada: int | None
) -> tuple[list[SolicitudDTO], str]:
    pendientes_lista = list(pendientes)
    if filtro_delegada is None:
        return pendientes_lista, "todas"
    seleccionadas = [sol for sol in pendientes_lista if sol.persona_id == filtro_delegada]
    return seleccionadas, f"delegada:{filtro_delegada}"


def resumen_confirmacion_pdf(creadas: Iterable[SolicitudDTO], errores: Iterable[str], modo: str) -> str:
    ids_confirmadas = [sol.id for sol in creadas if sol.id is not None]
    return f"Confirmadas: {len(ids_confirmadas)} · Errores: {len(list(errores))} · Modo: {modo}"


def ejecutar_exportacion_pdf_historico(
    *,
    operacion: Callable[[RequestExportacionPdfHistorico], Any],
    solicitudes: list[SolicitudDTO],
    persona: Persona,
    destino: Path,
    personas_por_id: dict[int, Persona],
    intro_text: str | None,
    logo_path: str | None,
    incrementar_metrica: Callable[[str], None],
    registrar_tiempo: Callable[[str, float], None],
) -> Path:
    started_at = time.perf_counter()
    resultado = cast(ResultadoExportacionPdfHistorico, operacion(
        RequestExportacionPdfHistorico(
            solicitudes=solicitudes,
            persona=persona,
            destino=destino,
            dry_run=False,
            overwrite=True,
            intro_text=intro_text,
            logo_path=logo_path,
            personas_por_id=personas_por_id,
        )
    ))
    if resultado.conflictos.no_ejecutable:
        raise BusinessRuleError("; ".join(resultado.conflictos.conflictos))
    incrementar_metrica("pdfs_generados")
    registrar_tiempo("latency.generar_pdf_ms", (time.perf_counter() - started_at) * 1000)
    return Path(resultado.artefactos_generados[0])


def construir_resumen_saldos_desde_valores(
    *,
    persona: Persona,
    filtro: PeriodoFiltro,
    consumidas_periodo: int,
    consumidas_anual: int,
    total_bolsa_anual: int,
    total_consumidas_anual: int,
    bolsa_grupo: int,
    construir_resumen: Callable[..., ResumenSaldosDTO],
) -> ResumenSaldosDTO:
    return construir_resumen(
        persona=persona,
        filtro=filtro,
        consumidas_periodo_min=consumidas_periodo,
        consumidas_anual_persona_min=consumidas_anual,
        total_bolsa_anual_min=total_bolsa_anual,
        total_consumidas_anual_min=total_consumidas_anual,
        bolsa_anual_grupo_min=bolsa_grupo,
    )


def confirmar_solicitudes_lote_con_manejador(
    solicitudes: Iterable[SolicitudDTO],
    *,
    resolver_o_crear: Callable[[SolicitudDTO], SolicitudDTO],
    construir_error_infra: Callable[[], str],
) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
    creadas: list[SolicitudDTO] = []
    pendientes: list[SolicitudDTO] = []
    errores: list[str] = []
    for solicitud in solicitudes:
        try:
            creadas.append(resolver_o_crear(solicitud))
        except (ValidacionError, BusinessRuleError) as exc:
            errores.append(str(exc))
            pendientes.append(solicitud)
        except PersistenceError:
            raise
        except InfraError:  # pragma: no cover - fallback
            errores.append(construir_error_infra())
            pendientes.append(solicitud)
    return creadas, pendientes, errores


def ejecutar_confirmar_sin_pdf_action(
    action_type: str,
    solicitud_id: int | None,
    solicitud: SolicitudDTO | None,
    *,
    obtener_existente: Callable[[int], SolicitudDTO | None],
    agregar_solicitud: Callable[[SolicitudDTO], SolicitudDTO],
    marcar_generada: Callable[[int], None],
) -> SolicitudDTO:
    if action_type == "RESOLVE_EXISTING":
        if solicitud_id is None:
            raise BusinessRuleError("La solicitud pendiente ya no existe.")
        creada = obtener_existente(solicitud_id)
        if creada is None:
            raise BusinessRuleError("La solicitud pendiente ya no existe.")
    else:
        if solicitud is None:
            raise BusinessRuleError("No se pudo confirmar la solicitud sin id.")
        creada = agregar_solicitud(solicitud)

    if creada.id is None:
        raise BusinessRuleError("No se pudo confirmar la solicitud sin id.")
    marcar_generada(creada.id)
    return creada


def confirmar_sin_pdf_con_manejador(
    acciones: Iterable[Any],
    *,
    ejecutar_accion: Callable[[Any], SolicitudDTO],
    obtener_solicitud: Callable[[Any], SolicitudDTO],
    construir_error_infra: Callable[[InfraError], str],
) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
    creadas_confirmadas: list[SolicitudDTO] = []
    pendientes_restantes: list[SolicitudDTO] = []
    errores: list[str] = []

    for action in acciones:
        try:
            creada = ejecutar_accion(action)
            creadas_confirmadas.append(creada)
        except (ValidacionError, BusinessRuleError) as exc:
            errores.append(str(exc))
            pendientes_restantes.append(obtener_solicitud(action))
        except PersistenceError:
            raise
        except InfraError as exc:  # pragma: no cover - fallback
            errores.append(construir_error_infra(exc))
            pendientes_restantes.append(obtener_solicitud(action))

    return creadas_confirmadas, pendientes_restantes, errores


def calcular_totales_globales_desde_fuentes(
    *,
    filtro: PeriodoFiltro,
    personas: list[Persona],
    listar_consumos: Callable[[int, int, int | None], list[int]],
    sumar_consumo: Callable[[list[int]], int],
    calcular_totales: Callable[..., TotalesGlobalesDTO],
) -> TotalesGlobalesDTO:
    mes = filtro.month if filtro.modo == "MENSUAL" else None
    consumidas_por_persona = [
        sumar_consumo(listar_consumos(persona.id or 0, filtro.year, mes))
        for persona in personas
    ]
    return calcular_totales(filtro=filtro, personas=personas, consumidas_por_persona=consumidas_por_persona)


def calcular_resumen_saldos_desde_fuentes(
    *,
    persona: Persona,
    persona_id: int,
    filtro: PeriodoFiltro,
    listar_periodo: Callable[[int, int, int | None], Iterable[Any]],
    sumar_consumo: Callable[[list[int]], int],
    acumular_consumo_anual: Callable[..., tuple[int, int]],
    bolsa_grupo: int,
    personas: list[Persona],
    construir_resumen: Callable[..., ResumenSaldosDTO],
) -> ResumenSaldosDTO:
    solicitudes_periodo = listar_periodo(
        persona_id,
        filtro.year,
        filtro.month if filtro.modo == "MENSUAL" else None,
    )
    solicitudes_ano = listar_periodo(persona_id, filtro.year, None)
    consumidas_periodo = sumar_consumo([s.horas_solicitadas_min for s in solicitudes_periodo])
    consumidas_anual = sumar_consumo([s.horas_solicitadas_min for s in solicitudes_ano])
    consumo_anual_por_persona = [
        sumar_consumo([s.horas_solicitadas_min for s in listar_periodo(p.id or 0, filtro.year, None)])
        for p in personas
    ]
    total_bolsa_anual, total_consumidas_anual = acumular_consumo_anual(
        personas=personas,
        consumo_anual_por_persona_min=consumo_anual_por_persona,
    )
    return construir_resumen(
        persona=persona,
        filtro=filtro,
        consumidas_periodo_min=consumidas_periodo,
        consumidas_anual_persona_min=consumidas_anual,
        total_bolsa_anual_min=total_bolsa_anual,
        total_consumidas_anual_min=total_consumidas_anual,
        bolsa_anual_grupo_min=bolsa_grupo,
    )
