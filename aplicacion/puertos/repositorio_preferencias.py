"""Puerto de persistencia para preferencias simples de UI."""

from __future__ import annotations

from typing import Protocol


class IRepositorioPreferencias(Protocol):
    """Contrato mínimo para leer y guardar preferencias booleanas."""

    def obtener_bool(self, clave: str, por_defecto: bool) -> bool:
        """Obtiene un valor booleano por clave."""

    def guardar_bool(self, clave: str, valor: bool) -> None:
        """Guarda un valor booleano por clave."""


    def obtener_texto(self, clave: str, por_defecto: str) -> str:
        """Obtiene un valor de texto por clave."""

    def guardar_texto(self, clave: str, valor: str) -> None:
        """Guarda un valor de texto por clave."""
