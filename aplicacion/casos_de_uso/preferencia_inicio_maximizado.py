"""Casos de uso para la preferencia de iniciar maximizada."""

from __future__ import annotations

from aplicacion.preferencias_claves import INICIAR_MAXIMIZADA
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias


class ObtenerPreferenciaInicioMaximizado:
    """Obtiene la preferencia de iniciar la app maximizada."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self) -> bool:
        return self._repositorio_preferencias.obtener_bool(
            INICIAR_MAXIMIZADA,
            por_defecto=False,
        )


class GuardarPreferenciaInicioMaximizado:
    """Guarda la preferencia de iniciar la app maximizada."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self, valor: bool) -> None:
        self._repositorio_preferencias.guardar_bool(INICIAR_MAXIMIZADA, valor)
