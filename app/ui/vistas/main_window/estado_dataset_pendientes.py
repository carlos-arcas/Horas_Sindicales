from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO


MOTIVO_EXCLUSION_DELEGADA_DISTINTA = "delegada_distinta"
MOTIVO_EXCLUSION_SIN_DELEGADA_ACTIVA = "sin_delegada_activa"


@dataclass(frozen=True)
class EstadoDatasetPendientes:
    pendientes_totales: list[SolicitudDTO]
    pendientes_visibles: list[SolicitudDTO]
    pendientes_ocultas: list[SolicitudDTO]
    pendientes_otras_delegadas: list[SolicitudDTO]
    motivos_exclusion: dict[int | None, str]



def calcular_estado_dataset_pendientes(
    *,
    pendientes_totales: list[SolicitudDTO],
    delegada_activa_id: int | None,
    ver_todas_delegadas: bool,
) -> EstadoDatasetPendientes:
    if ver_todas_delegadas:
        return EstadoDatasetPendientes(
            pendientes_totales=list(pendientes_totales),
            pendientes_visibles=list(pendientes_totales),
            pendientes_ocultas=[],
            pendientes_otras_delegadas=[],
            motivos_exclusion={},
        )

    if delegada_activa_id is None:
        motivos = {solicitud.id: MOTIVO_EXCLUSION_SIN_DELEGADA_ACTIVA for solicitud in pendientes_totales}
        return EstadoDatasetPendientes(
            pendientes_totales=list(pendientes_totales),
            pendientes_visibles=[],
            pendientes_ocultas=list(pendientes_totales),
            pendientes_otras_delegadas=list(pendientes_totales),
            motivos_exclusion=motivos,
        )

    visibles: list[SolicitudDTO] = []
    ocultas: list[SolicitudDTO] = []
    ocultas_otras_delegadas: list[SolicitudDTO] = []
    motivos_exclusion: dict[int | None, str] = {}

    for solicitud in pendientes_totales:
        if solicitud.persona_id == delegada_activa_id:
            visibles.append(solicitud)
            continue
        ocultas.append(solicitud)
        ocultas_otras_delegadas.append(solicitud)
        motivos_exclusion[solicitud.id] = MOTIVO_EXCLUSION_DELEGADA_DISTINTA

    return EstadoDatasetPendientes(
        pendientes_totales=list(pendientes_totales),
        pendientes_visibles=visibles,
        pendientes_ocultas=ocultas,
        pendientes_otras_delegadas=ocultas_otras_delegadas,
        motivos_exclusion=motivos_exclusion,
    )
