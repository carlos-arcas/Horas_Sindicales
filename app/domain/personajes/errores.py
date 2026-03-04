from __future__ import annotations


class ErrorDominioPersonaje(ValueError):
    """Error base de dominio para personajes."""


class NombrePersonajeInvalido(ErrorDominioPersonaje):
    """Se dispara cuando el nombre no cumple reglas de dominio."""


class DescripcionPersonajeInvalida(ErrorDominioPersonaje):
    """Se dispara cuando la descripción supera límites permitidos."""
