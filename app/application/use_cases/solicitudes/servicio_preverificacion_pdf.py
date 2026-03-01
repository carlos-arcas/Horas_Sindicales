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
    rango: tuple[str, ...]
    prefijo: str = ""
    carpeta_destino: str = ""


@dataclass(frozen=True)
class ResultadoPreverificacionPdf:
    ruta_destino: str
    colision: bool
    ruta_sugerida: str | None
    motivos: tuple[str, ...]


class ServicioPreverificacionPdf:
    def __init__(self, fs: SistemaArchivosPuerto, generador_pdf: GeneradorPdfPuerto | None) -> None:
        self._fs = fs
        self._generador_pdf = generador_pdf

    def construir_nombre_pdf(self, entrada: EntradaNombrePdf) -> str:
        if self._generador_pdf is None:
            raise ValueError("No hay generador PDF configurado.")
        nombre = self._generador_pdf.construir_nombre_archivo(
            entrada.nombre_persona,
            list(entrada.rango),
        )
        nombre_normalizado = _normalizar_nombre_pdf(nombre)
        return _aplicar_prefijo(nombre_normalizado, entrada.prefijo)

    def construir_ruta_destino(self, entrada: EntradaNombrePdf) -> str:
        nombre_pdf = self.construir_nombre_pdf(entrada)
        base = Path(entrada.carpeta_destino).expanduser()
        return str((base / nombre_pdf).resolve(strict=False))

    def preverificar_ruta(self, ruta: str) -> ResultadoPreverificacionPdf:
        destino = Path(ruta).resolve(strict=False)
        if not self._fs.existe(destino):
            return ResultadoPreverificacionPdf(
                ruta_destino=str(destino),
                colision=False,
                ruta_sugerida=None,
                motivos=(),
            )
        sugerida = self.proponer_ruta_alternativa(str(destino))
        return ResultadoPreverificacionPdf(
            ruta_destino=str(destino),
            colision=True,
            ruta_sugerida=sugerida,
            motivos=(f"Colisión de ruta destino: {destino}",),
        )

    def proponer_ruta_alternativa(self, ruta: str, *, limite: int = 9_999) -> str | None:
        destino = Path(ruta).resolve(strict=False)
        stem = destino.stem
        suffix = destino.suffix or ".pdf"
        parent = destino.parent
        for indice in range(1, limite + 1):
            candidata = parent / f"{stem}({indice}){suffix}"
            if not self._fs.existe(candidata):
                return str(candidata)
        return None


def _normalizar_nombre_pdf(nombre: str) -> str:
    limpio = _REEMPLAZO_NOMBRE.sub("_", nombre.strip())
    compacto = _REEMPLAZO_ESPACIOS.sub("_", limpio)
    if not compacto:
        return "solicitudes.pdf"
    if not compacto.lower().endswith(".pdf"):
        return f"{compacto}.pdf"
    return compacto


def _aplicar_prefijo(nombre_pdf: str, prefijo: str) -> str:
    prefijo_limpio = _normalizar_segmento(prefijo)
    if not prefijo_limpio:
        return nombre_pdf
    return f"{prefijo_limpio}_{nombre_pdf}"


def _normalizar_segmento(texto: str) -> str:
    limpio = _REEMPLAZO_NOMBRE.sub("_", texto.strip())
    return _REEMPLAZO_ESPACIOS.sub("_", limpio).strip("_")
