from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


EstadoConfirmacionPdf = Literal[
    "OK_CON_PDF",
    "OK_SIN_PDF",
    "SIN_CONFIRMADAS",
    "ERROR_INSERCION",
    "ERROR_PDF",
    "ERROR_PRECONDICION",
]


@dataclass(frozen=True)
class SolicitudConfirmarPdfPeticion:
    pendientes_ids: list[int]
    generar_pdf: bool
    destino_pdf: Path | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class SolicitudConfirmarPdfResultado:
    estado: EstadoConfirmacionPdf = "ERROR_PRECONDICION"
    confirmadas: int = 0
    confirmadas_ids: list[int] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    pdf_generado: Path | None = None
    sync_permitido: bool = False
    pendientes_restantes: list[int] | None = None

    @property
    def ruta_pdf(self) -> Path | None:
        """Alias legado para compatibilidad incremental con consumidores existentes."""
        return self.pdf_generado

    def __post_init__(self) -> None:
        if self.confirmadas != len(self.confirmadas_ids):
            raise ValueError("El total de confirmadas debe coincidir con confirmadas_ids.")
        if self.errores and self.pdf_generado is not None:
            raise ValueError("No puede existir pdf_generado cuando hay errores.")
        if self.sync_permitido and self.pdf_generado is None:
            raise ValueError("sync_permitido requiere pdf_generado.")
