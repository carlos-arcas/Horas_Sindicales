from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ToastDTO:
    """DTO de visualización consumido por la UI del sistema Toast."""

    id: str
    titulo: str
    mensaje: str
    nivel: str = "info"
    detalles: str | None = None
    codigo: str | None = None
    correlacion_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    duracion_ms: int = 8000
