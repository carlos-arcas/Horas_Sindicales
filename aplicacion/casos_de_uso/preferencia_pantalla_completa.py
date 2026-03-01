"""Casos de uso para la preferencia de pantalla completa."""

from __future__ import annotations

from aplicacion.preferencias_claves import PANTALLA_COMPLETA
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias


class ObtenerPreferenciaPantallaCompleta:
    """Obtiene la preferencia de pantalla completa."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self) -> bool:
        return self._repositorio_preferencias.obtener_bool(
            PANTALLA_COMPLETA,
            por_defecto=False,
        )


class GuardarPreferenciaPantallaCompleta:
    """Guarda la preferencia de pantalla completa."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self, valor: bool) -> None:
        self._repositorio_preferencias.guardar_bool(PANTALLA_COMPLETA, valor)
