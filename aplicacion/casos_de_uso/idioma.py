"""Casos de uso para la preferencia de idioma de UI."""

from __future__ import annotations

from aplicacion.preferencias_claves import IDIOMA_UI
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias


class ObtenerIdiomaUI:
    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self) -> str:
        return self._repositorio_preferencias.obtener_texto(IDIOMA_UI, por_defecto="es")


class GuardarIdiomaUI:
    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self, idioma: str) -> None:
        self._repositorio_preferencias.guardar_texto(IDIOMA_UI, idioma)
