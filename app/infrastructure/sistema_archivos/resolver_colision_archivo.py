from __future__ import annotations

from pathlib import Path


def resolver_ruta_sin_colision(path: Path, *, limite: int = 9_999) -> Path:
    """Retorna la primera ruta libre usando sufijo " (n)" cuando existe colisión."""
    ruta_base = path.resolve(strict=False)
    if not ruta_base.exists():
        return ruta_base

    stem = ruta_base.stem
    suffix = ruta_base.suffix
    for indice in range(2, limite + 1):
        candidata = ruta_base.parent / f"{stem} ({indice}){suffix}"
        if not candidata.exists():
            return candidata.resolve(strict=False)
    return ruta_base
