from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ConfirmarPdfRequestDTO:
    pendientes_ids: list[int]
    generar_pdf: bool
    destino_pdf: Path | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class ConfirmarPdfResultDTO:
    confirmadas_ids: list[int] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    ruta_pdf: Path | None = None
    pendientes_restantes: list[int] | None = None
