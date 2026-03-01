"""DTOs del sistema de notificaciones Toast."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class NivelToast(str, Enum):
    """Niveles soportados para notificaciones Toast."""

    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(slots=True)
class NotificacionToast:
    """Representa una notificación Toast para la capa de aplicación."""

    nivel: NivelToast
    titulo: str
    mensaje: str
    detalles: Optional[str] = None
    codigo: Optional[str] = None
    correlacion_id: Optional[str] = None
    duracion_ms: int = 8000
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self._validar_campos_obligatorios()
        self._validar_duracion()

    def _validar_campos_obligatorios(self) -> None:
        if not self.titulo.strip():
            raise ValueError("titulo no puede estar vacío")

        if not self.mensaje.strip():
            raise ValueError("mensaje no puede estar vacío")

    def _validar_duracion(self) -> None:
        if self.duracion_ms <= 0:
            raise ValueError("duracion_ms debe ser mayor a 0")
