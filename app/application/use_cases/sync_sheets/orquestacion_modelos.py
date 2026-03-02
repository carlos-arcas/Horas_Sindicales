from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HEADER_CANONICO_SOLICITUDES = [
    "uuid",
    "delegada_uuid",
    "delegada_nombre",
    "fecha",
    "desde_h",
    "desde_m",
    "hasta_h",
    "hasta_m",
    "completo",
    "minutos_total",
    "notas",
    "estado",
    "created_at",
    "updated_at",
    "source_device",
    "deleted",
    "pdf_id",
]


@dataclass
class PullApplyContext:
    worksheet: Any
    headers: list[str]
    row_number: int
    row: dict[str, Any]
    uuid_value: str
    local_row: Any | None
    stats: dict[str, Any]
