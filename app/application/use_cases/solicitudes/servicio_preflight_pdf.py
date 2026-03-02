from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto

_REEMPLAZO_NOMBRE = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')
_REEMPLAZO_ESPACIOS = re.compile(r"\s+")
_REEMPLAZO_PUNTO_ESPACIO_FINAL = re.compile(r"[. ]+$")
_NOMBRES_RESERVADOS_WINDOWS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

logger = logging.getLogger(__name__)


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
        base_dir_permitido: Path | None = None,
    ) -> None:
        self._fs = fs
        self._generador_pdf = generador_pdf
        self._base_dir_permitido = _resolver_base_dir_permitido(base_dir_permitido)

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
        destino = Path(carpeta).expanduser() / nombre_pdf
        return self._normalizar_y_validar_destino(destino)

    def validar_colision(self, ruta: str) -> ResultadoPreflightPdf:
        destino = self._normalizar_y_validar_destino(Path(ruta).expanduser())
        if not self._existe_ruta(destino):
            self._log_destino_seguro(Path(destino), "pdf_preflight_destino_disponible")
            return ResultadoPreflightPdf(
                ruta_destino=destino,
                colision=False,
                ruta_sugerida=None,
                motivos=(),
            )
        sugerida = self.sugerir_ruta_alternativa(destino)
        self._log_destino_seguro(Path(destino), "pdf_preflight_destino_colision")
        return ResultadoPreflightPdf(
            ruta_destino=destino,
            colision=True,
            ruta_sugerida=sugerida,
            motivos=(f"Colisión de ruta destino: {destino}",),
        )

    def sugerir_ruta_alternativa(self, ruta: str, *, limite: int = 9_999) -> str | None:
        destino = Path(self._normalizar_y_validar_destino(Path(ruta)))
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

    def _normalizar_y_validar_destino(self, ruta: Path) -> str:
        destino = Path(_normalizar_ruta(ruta))
        _validar_destino_bajo_base(destino, self._base_dir_permitido)
        return str(destino)

    def _log_destino_seguro(self, destino: Path, evento: str) -> None:
        logger.info(
            evento,
            extra={
                "extra": {
                    "archivo": destino.name,
                    "carpeta": str(destino.parent),
                }
            },
        )


def _normalizar_ruta(ruta: Path) -> str:
    return str(ruta.resolve(strict=False))


def _normalizar_nombre_pdf(nombre: str) -> str:
    limpio = _REEMPLAZO_NOMBRE.sub("_", nombre.strip())
    compacto = _REEMPLAZO_ESPACIOS.sub("_", limpio)
    compacto = _REEMPLAZO_PUNTO_ESPACIO_FINAL.sub("", compacto)
    compacto = _normalizar_nombre_reservado_windows(compacto)
    if not compacto:
        return "solicitudes.pdf"
    if not compacto.lower().endswith(".pdf"):
        return f"{compacto}.pdf"
    return compacto


def _normalizar_nombre_reservado_windows(nombre: str) -> str:
    stem = Path(nombre).stem.upper()
    if stem in _NOMBRES_RESERVADOS_WINDOWS:
        return f"{nombre}_archivo"
    return nombre


def _resolver_base_dir_permitido(base_dir_permitido: Path | None) -> Path | None:
    if base_dir_permitido is None:
        return None
    return base_dir_permitido.expanduser().resolve(strict=False)


def _validar_destino_bajo_base(destino: Path, base_dir_permitido: Path | None) -> None:
    if base_dir_permitido is None:
        return
    try:
        destino.relative_to(base_dir_permitido)
    except ValueError as exc:
        raise ValueError(
            "El destino PDF debe estar dentro del directorio permitido configurado."
        ) from exc
