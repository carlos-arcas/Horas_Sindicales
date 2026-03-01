"""Casos de uso vinculados al estado de onboarding."""

from __future__ import annotations

from aplicacion.preferencias_claves import ONBOARDING_COMPLETADO
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias


class ObtenerEstadoOnboarding:
    """Consulta si el onboarding ya fue completado."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self) -> bool:
        return self._repositorio_preferencias.obtener_bool(
            ONBOARDING_COMPLETADO,
            por_defecto=False,
        )


class MarcarOnboardingCompletado:
    """Marca el onboarding como completado."""

    def __init__(self, repositorio_preferencias: IRepositorioPreferencias) -> None:
        self._repositorio_preferencias = repositorio_preferencias

    def ejecutar(self) -> None:
        self._repositorio_preferencias.guardar_bool(ONBOARDING_COMPLETADO, True)
