from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EstadoMainWindow:
    """Estado de interfaz para operaciones de sincronización."""

    sync_en_progreso: bool = False
