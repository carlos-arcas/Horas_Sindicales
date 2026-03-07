from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO


@dataclass(frozen=True)
class EntradaEstadoPostConfirmacion:
    confirmadas_ids: list[int]
    pendientes_restantes: list[SolicitudDTO] | None
    pending_all_solicitudes: list[SolicitudDTO]
    pending_solicitudes: list[SolicitudDTO]
    hidden_pendientes: list[SolicitudDTO]
    pending_otras_delegadas: list[SolicitudDTO]
    orphan_pendientes: list[SolicitudDTO]


@dataclass(frozen=True)
class EstadoPostConfirmacion:
    pending_all_solicitudes: list[SolicitudDTO]
    pending_solicitudes: list[SolicitudDTO]
    hidden_pendientes: list[SolicitudDTO]
    pending_otras_delegadas: list[SolicitudDTO]
    orphan_pendientes: list[SolicitudDTO]
    confirmadas_aplicadas_ids: list[int]


def aplicar_confirmacion_en_lista(pendientes: list[SolicitudDTO], confirmadas_ids: list[int]) -> list[SolicitudDTO]:
    confirmadas_set = set(confirmadas_ids)
    return [solicitud for solicitud in pendientes if solicitud.id is None or solicitud.id not in confirmadas_set]


def resolver_estado_post_confirmacion(entrada: EntradaEstadoPostConfirmacion) -> EstadoPostConfirmacion:
    ids_previos = {sol.id for sol in entrada.pending_all_solicitudes if sol.id is not None}

    if entrada.pendientes_restantes is not None:
        restantes_ids = {sol.id for sol in entrada.pendientes_restantes if sol.id is not None}
        return EstadoPostConfirmacion(
            pending_solicitudes=list(entrada.pendientes_restantes),
            pending_all_solicitudes=_filtrar_por_restantes(entrada.pending_all_solicitudes, restantes_ids),
            hidden_pendientes=_filtrar_por_restantes(entrada.hidden_pendientes, restantes_ids),
            pending_otras_delegadas=_filtrar_por_restantes(entrada.pending_otras_delegadas, restantes_ids),
            orphan_pendientes=_filtrar_por_restantes(entrada.orphan_pendientes, restantes_ids),
            confirmadas_aplicadas_ids=[
                solicitud_id
                for solicitud_id in entrada.confirmadas_ids
                if solicitud_id in ids_previos and solicitud_id not in restantes_ids
            ],
        )

    return EstadoPostConfirmacion(
        pending_all_solicitudes=aplicar_confirmacion_en_lista(entrada.pending_all_solicitudes, entrada.confirmadas_ids),
        pending_solicitudes=aplicar_confirmacion_en_lista(entrada.pending_solicitudes, entrada.confirmadas_ids),
        hidden_pendientes=aplicar_confirmacion_en_lista(entrada.hidden_pendientes, entrada.confirmadas_ids),
        pending_otras_delegadas=aplicar_confirmacion_en_lista(entrada.pending_otras_delegadas, entrada.confirmadas_ids),
        orphan_pendientes=aplicar_confirmacion_en_lista(entrada.orphan_pendientes, entrada.confirmadas_ids),
        confirmadas_aplicadas_ids=[solicitud_id for solicitud_id in entrada.confirmadas_ids if solicitud_id in ids_previos],
    )


def _filtrar_por_restantes(pendientes: list[SolicitudDTO], restantes_ids: set[int]) -> list[SolicitudDTO]:
    return [solicitud for solicitud in pendientes if solicitud.id is None or solicitud.id in restantes_ids]
