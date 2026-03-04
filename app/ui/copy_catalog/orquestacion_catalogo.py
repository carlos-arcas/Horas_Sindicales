from __future__ import annotations

from functools import lru_cache

from .storage_catalogo import leer_catalogo_json


@lru_cache(maxsize=1)
def obtener_catalogo() -> dict[str, str]:
    return leer_catalogo_json()


def recargar_catalogo() -> dict[str, str]:
    obtener_catalogo.cache_clear()
    return obtener_catalogo()
