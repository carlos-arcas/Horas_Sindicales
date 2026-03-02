from __future__ import annotations

from pathlib import Path

from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto


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
