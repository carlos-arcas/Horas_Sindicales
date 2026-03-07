from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ui.copy_catalog import copy_text


class ProtocoloEstadoDatasetPendientes(Protocol):
    pendientes_ocultas: list[object]
    pendientes_otras_delegadas: list[object]


@dataclass(frozen=True, slots=True)
class EstadoVistaPendientes:
    warning_visible: bool
    warning_text: str
    revisar_visible: bool
    revisar_text: str


def construir_estado_vista_pendientes(
    *,
    estado_dataset: ProtocoloEstadoDatasetPendientes,
    ver_todas_delegadas: bool,
) -> EstadoVistaPendientes:
    hidden_count = len(estado_dataset.pendientes_ocultas)
    otras_delegadas_count = len(estado_dataset.pendientes_otras_delegadas)
    warning_visible = hidden_count > 0 and not ver_todas_delegadas
    if not warning_visible:
        return EstadoVistaPendientes(False, "", False, "")
    return EstadoVistaPendientes(
        True,
        f"{copy_text('ui.data_refresh.pendientes_otras_delegadas')} {otras_delegadas_count}",
        True,
        f"{copy_text('ui.data_refresh.revisar_pendientes_ocultas_prefix')}{hidden_count})",
    )
