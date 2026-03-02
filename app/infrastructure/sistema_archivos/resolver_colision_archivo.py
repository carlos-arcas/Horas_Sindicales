from __future__ import annotations

from pathlib import Path


def resolver_colision_archivo(
    destino: Path, *, inicio: int = 2, limite: int = 9_999
) -> Path:
    """Devuelve una ruta disponible aplicando sufijos deterministas " (n)"."""
    ruta_base = destino.resolve(strict=False)
    if not ruta_base.exists():
        return ruta_base

    stem = ruta_base.stem
    suffix = ruta_base.suffix
    indice_inicial = max(inicio, 2)
    for indice in range(indice_inicial, limite + 1):
        candidata = ruta_base.parent / f"{stem} ({indice}){suffix}"
        candidata_resuelta = candidata.resolve(strict=False)
        if not candidata_resuelta.exists():
            return candidata_resuelta
    return ruta_base
