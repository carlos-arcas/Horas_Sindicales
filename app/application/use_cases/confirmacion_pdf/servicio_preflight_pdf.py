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
        return _normalizar_ruta(Path(carpeta).expanduser() / nombre_pdf)

    def validar_colision(self, ruta: str) -> ResultadoPreflightPdf:
        destino = _normalizar_ruta(Path(ruta).expanduser())
        if not self._existe_ruta(destino):
            return ResultadoPreflightPdf(
                ruta_destino=destino,
                colision=False,
                ruta_sugerida=None,
                motivos=(),
            )
        sugerida = self.sugerir_ruta_alternativa(destino)
        return ResultadoPreflightPdf(
            ruta_destino=destino,
            colision=True,
            ruta_sugerida=sugerida,
            motivos=(f"Colisión de ruta destino: {destino}",),
        )

    def sugerir_ruta_alternativa(self, ruta: str, *, limite: int = 9_999) -> str | None:
        destino = Path(_normalizar_ruta(Path(ruta)))
        stem = destino.stem
        suffix = destino.suffix or ".pdf"
        for indice in range(1, limite + 1):
            candidata = destino.parent / f"{stem}({indice}){suffix}"
            candidata_str = _normalizar_ruta(candidata)
            if not self._existe_ruta(candidata_str):
                return candidata_str
        return None

    def _existe_ruta(self, ruta: str) -> bool:
        path = Path(ruta)
        existe_ruta = getattr(self._fs, "existe_ruta", None)
        if callable(existe_ruta):
            return bool(existe_ruta(path))
        return bool(self._fs.existe(path))


def _normalizar_ruta(ruta: Path) -> str:
    return str(ruta.resolve(strict=False))


def _normalizar_nombre_pdf(nombre: str) -> str:
    limpio = _REEMPLAZO_NOMBRE.sub("_", nombre.strip())
    compacto = _REEMPLAZO_ESPACIOS.sub("_", limpio)
    if not compacto:
        return "solicitudes.pdf"
    if not compacto.lower().endswith(".pdf"):
        return f"{compacto}.pdf"
    return compacto
