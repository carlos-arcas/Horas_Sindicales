from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Personaje:
    id: UUID
    proyecto_id: UUID
    nombre: str
    descripcion: str
    creado_en: datetime
    actualizado_en: datetime
