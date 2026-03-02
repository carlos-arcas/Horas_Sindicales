from __future__ import annotations

import re
from pathlib import Path

from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto

_PATRON_SUFFIX_INDICE = re.compile(r"^(?P<base>.+) \((?P<indice>\d+)\)$")


def resolver_colision_archivo(
    destino: Path, fs: SistemaArchivosPuerto, *, limite: int = 9_999
) -> Path:
    """Resuelve colisiones incrementando el sufijo " (n)" desde el destino recibido."""
    destino_resuelto = destino.resolve(strict=False)
    if not _existe(destino_resuelto, fs):
        return destino_resuelto

    stem_base, indice_inicial = _extraer_base_e_indice(destino_resuelto.stem)
    suffix = destino_resuelto.suffix or ".pdf"
    parent = destino_resuelto.parent
    for indice in range(indice_inicial + 1, limite + 1):
        candidata = (parent / f"{stem_base} ({indice}){suffix}").resolve(strict=False)
        if not _existe(candidata, fs):
            return candidata
    return destino_resuelto


def resolver_colision_pdf(
    destino: Path, fs: SistemaArchivosPuerto, *, limite: int = 9_999
) -> Path:
    """Resuelve un destino PDF sin colisión usando un sufijo determinista " (n)"."""
    return resolver_colision_archivo(destino, fs, limite=limite)


def _extraer_base_e_indice(stem: str) -> tuple[str, int]:
    coincidencia = _PATRON_SUFFIX_INDICE.match(stem)
    if coincidencia is None:
        return stem, 0
    return coincidencia.group("base"), int(coincidencia.group("indice"))


def _existe(ruta: Path, fs: SistemaArchivosPuerto) -> bool:
    existe_ruta = getattr(fs, "existe_ruta", None)
    if callable(existe_ruta):
        return bool(existe_ruta(ruta))
    return bool(fs.existe(ruta))
