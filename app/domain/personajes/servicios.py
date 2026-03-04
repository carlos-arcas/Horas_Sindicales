from __future__ import annotations

from app.domain.personajes.errores import DescripcionPersonajeInvalida, NombrePersonajeInvalido

MAX_DESCRIPCION = 1200
MAX_NOMBRE = 80


def normalizar_nombre_personaje(nombre: str) -> str:
    nombre_normalizado = " ".join(nombre.strip().split())
    if not nombre_normalizado:
        raise NombrePersonajeInvalido("personajes.nombre_vacio")
    if len(nombre_normalizado) > MAX_NOMBRE:
        raise NombrePersonajeInvalido("personajes.nombre_demasiado_largo")
    return nombre_normalizado


def validar_descripcion_personaje(descripcion: str) -> str:
    descripcion_limpia = descripcion.strip()
    if len(descripcion_limpia) > MAX_DESCRIPCION:
        raise DescripcionPersonajeInvalida("personajes.descripcion_demasiado_larga")
    return descripcion_limpia
