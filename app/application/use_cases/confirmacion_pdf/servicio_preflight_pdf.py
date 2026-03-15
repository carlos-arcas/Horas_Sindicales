from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.application.dto import SolicitudDTO
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.application.use_cases.solicitudes.auxiliares_caso_uso import (
    NOMBRE_PDF_POR_DEFECTO,
    ResolucionDestinoPdf,
    resolver_destino_pdf,
)
from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_pdf,
    resolver_ruta_sin_colision,
)
from app.domain.ports import PersonaRepository

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


class ServicioDestinoPdfConfirmacion:
    def __init__(
        self,
        *,
        persona_repo: PersonaRepository,
        fs: SistemaArchivosPuerto,
        generador_pdf: GeneradorPdfPuerto | None,
    ) -> None:
        self._persona_repo = persona_repo
        self._fs = fs
        self._servicio_preflight_pdf = ServicioPreflightPdf(
            fs=fs,
            generador_pdf=generador_pdf,
        )

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_lista = list(solicitudes)
        if not solicitudes_lista:
            return NOMBRE_PDF_POR_DEFECTO
        persona = self._persona_repo.get_by_id(solicitudes_lista[0].persona_id)
        if persona is None:
            raise ValueError("Persona no encontrada.")
        fechas = tuple(solicitud.fecha_pedida for solicitud in solicitudes_lista)
        return self._servicio_preflight_pdf.construir_nombre_pdf(
            EntradaNombrePdf(nombre_persona=persona.nombre, fechas=fechas)
        )

    def resolver_destino_pdf(
        self,
        destino: Path,
        *,
        overwrite: bool = False,
        auto_rename: bool = True,
    ) -> ResolucionDestinoPdf:
        if hasattr(self._fs, "resolver_colision_archivo"):
            resolver_colision = resolver_ruta_sin_colision
        else:

            def resolver_colision(ruta: Path) -> Path:
                return resolver_colision_pdf(ruta, self._fs)

        ruta_destino, colision_detectada, ruta_original, ruta_alternativa = (
            resolver_destino_pdf(
                destino,
                overwrite=overwrite,
                auto_rename=auto_rename,
                resolver_ruta_colision=resolver_colision,
            )
        )
        return ResolucionDestinoPdf(
            ruta_destino=ruta_destino,
            colision_detectada=colision_detectada,
            ruta_original=ruta_original,
            ruta_alternativa=ruta_alternativa if colision_detectada else None,
        )


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
