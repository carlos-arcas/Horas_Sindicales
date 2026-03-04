
"""Catálogo centralizado de textos de interfaz."""

from .diff_catalogo import calcular_diff_catalogos, fusionar_catalogos
from .modelos import CambioCatalogo, EntradaCatalogo, ResultadoDiff
from .orquestacion_catalogo import obtener_catalogo, recargar_catalogo
from .parseo_catalogo import parsear_catalogo_crudo, seleccionar_claves
from .storage_catalogo import escribir_catalogo_json, leer_catalogo_json


def copy_text(key: str) -> str:
    """Devuelve un texto de UI por clave estable.

    Lanza ``KeyError`` si falta la clave para detectar regresiones en tests.
    """

    return obtener_catalogo()[key]


def copy_keys() -> tuple[str, ...]:
    """Expone las claves disponibles para validación en tests."""

    return tuple(obtener_catalogo().keys())


__all__ = [
    "CambioCatalogo",
    "EntradaCatalogo",
    "ResultadoDiff",
    "calcular_diff_catalogos",
    "copy_keys",
    "copy_text",
    "escribir_catalogo_json",
    "fusionar_catalogos",
    "leer_catalogo_json",
    "obtener_catalogo",
    "parsear_catalogo_crudo",
    "recargar_catalogo",
    "seleccionar_claves",
]
