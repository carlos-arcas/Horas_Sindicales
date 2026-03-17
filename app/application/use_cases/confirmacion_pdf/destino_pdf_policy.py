from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto


NOMBRE_PDF_POR_DEFECTO = "A_Coordinadora_Solicitud_Horas_Sindicales.pdf"


@dataclass(frozen=True)
class ResolucionDestinoPdf:
    ruta_destino: Path
    colision_detectada: bool
    ruta_original: Path
    ruta_alternativa: Path | None


def resolver_destino_pdf(
    destino: Path,
    *,
    overwrite: bool,
    auto_rename: bool,
    resolver_ruta_colision: Callable[[Path], Path],
) -> tuple[Path, bool, Path, Path | None]:
    ruta_original = destino.resolve(strict=False)
    ruta_alternativa = resolver_ruta_colision(ruta_original)
    colision_detectada = ruta_alternativa != ruta_original

    if overwrite or not colision_detectada:
        ruta_destino = ruta_original
    elif auto_rename:
        ruta_destino = ruta_alternativa
    else:
        ruta_destino = ruta_original

    alternativa = ruta_alternativa if colision_detectada else None
    return ruta_destino, colision_detectada, ruta_original, alternativa


def resolver_ruta_sin_colision(ruta: Path) -> Path:
    """Devuelve una ruta PDF libre aplicando sufijo incremental determinista."""
    ruta_resuelta = ruta.resolve(strict=False)
    if not ruta_resuelta.exists():
        return ruta_resuelta

    stem = ruta_resuelta.stem
    suffix = ruta_resuelta.suffix
    for indice in range(1, 1_000):
        candidata = ruta_resuelta.parent / f"{stem} ({indice}){suffix}"
        candidata_resuelta = candidata.resolve(strict=False)
        if not candidata_resuelta.exists():
            return candidata_resuelta

    raise ValueError(
        f"No se pudo resolver una ruta libre para '{ruta_resuelta}' tras 999 intentos."
    )


def resolver_colision_pdf(
    destino: Path, fs: SistemaArchivosPuerto, *, limite: int = 9_999
) -> Path:
    """Resuelve un destino PDF sin colisión usando un sufijo determinista " (n)"."""
    destino_resuelto = destino.resolve(strict=False)

    resolver_fs = getattr(fs, "resolver_colision_archivo", None)
    if callable(resolver_fs):
        return Path(resolver_fs(destino_resuelto, inicio=1, limite=limite)).resolve(
            strict=False
        )

    if not _existe(destino_resuelto, fs):
        return destino_resuelto

    stem = destino_resuelto.stem
    suffix = destino_resuelto.suffix or ".pdf"
    for indice in range(1, limite + 1):
        candidata = destino_resuelto.parent / f"{stem} ({indice}){suffix}"
        candidata_resuelta = candidata.resolve(strict=False)
        if not _existe(candidata_resuelta, fs):
            return candidata_resuelta
    return destino_resuelto


def _existe(ruta: Path, fs: SistemaArchivosPuerto) -> bool:
    existe_ruta = getattr(fs, "existe_ruta", None)
    if callable(existe_ruta):
        return bool(existe_ruta(ruta))
    return bool(fs.existe(ruta))

