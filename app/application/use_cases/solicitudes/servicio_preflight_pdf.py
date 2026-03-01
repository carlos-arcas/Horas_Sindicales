from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto

_REEMPLAZO_NOMBRE = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')
_REEMPLAZO_ESPACIOS = re.compile(r"\s+")


@dataclass(frozen=True)
class EntradaNombrePdf:
    nombre_persona: str
    fechas: tuple[str, ...]


@dataclass(frozen=True)
class ResultadoPreflightPdf:
    ruta_destino: str
    colision: bool
    ruta_sugerida: str | None
    motivos: tuple[str, ...]


class ServicioPreflightPdf:
    def __init__(
        self,
        fs: SistemaArchivosPuerto,
        generador_pdf: GeneradorPdfPuerto | None,
    ) -> None:
        self._fs = fs
        self._generador_pdf = generador_pdf

    def construir_nombre_pdf(self, entrada: EntradaNombrePdf) -> str:
        if self._generador_pdf is None:
            raise ValueError("No hay generador PDF configurado.")
        nombre = self._generador_pdf.construir_nombre_archivo(
            entrada.nombre_persona,
            list(entrada.fechas),
        )
        return _normalizar_nombre_pdf(nombre)

    def construir_ruta_destino(self, entrada: EntradaNombrePdf, carpeta: str) -> str:
        nombre_pdf = self.construir_nombre_pdf(entrada)
        base = Path(carpeta).expanduser()
        return str((base / nombre_pdf).resolve(strict=False))

    def validar_colision(self, ruta: str) -> ResultadoPreflightPdf:
        destino = Path(ruta)
        destino_normalizado = destino.resolve(strict=False)
        if not self._fs.existe(destino_normalizado):
            return ResultadoPreflightPdf(
                ruta_destino=str(destino_normalizado),
                colision=False,
                ruta_sugerida=None,
                motivos=(),
            )
        ruta_sugerida = self._proponer_ruta_alternativa(destino_normalizado)
        return ResultadoPreflightPdf(
            ruta_destino=str(destino_normalizado),
            colision=True,
            ruta_sugerida=ruta_sugerida,
            motivos=(f"Colisión de ruta destino: {destino_normalizado}",),
        )

    def _proponer_ruta_alternativa(self, destino: Path) -> str | None:
        stem = destino.stem
        suffix = destino.suffix or ".pdf"
        parent = destino.parent
        for index in range(1, 10_000):
            candidate = parent / f"{stem}({index}){suffix}"
            if not self._fs.existe(candidate):
                return str(candidate)
        return None


def _normalizar_nombre_pdf(nombre: str) -> str:
    limpio = _REEMPLAZO_NOMBRE.sub("_", nombre.strip())
    compacto = _REEMPLAZO_ESPACIOS.sub("_", limpio)
    if not compacto:
        return "solicitudes.pdf"
    if not compacto.lower().endswith(".pdf"):
        return f"{compacto}.pdf"
    return compacto
