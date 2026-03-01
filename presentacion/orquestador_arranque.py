from __future__ import annotations

from dataclasses import dataclass

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from aplicacion.casos_de_uso.idioma import GuardarIdiomaUI, ObtenerIdiomaUI
from aplicacion.casos_de_uso.onboarding import MarcarOnboardingCompletado, ObtenerEstadoOnboarding
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from presentacion.i18n import I18nManager


@dataclass
class DependenciasArranque:
    obtener_estado_onboarding: ObtenerEstadoOnboarding
    marcar_onboarding_completado: MarcarOnboardingCompletado
    guardar_preferencia_pantalla_completa: GuardarPreferenciaPantallaCompleta
    obtener_preferencia_pantalla_completa: ObtenerPreferenciaPantallaCompleta
    obtener_idioma_ui: ObtenerIdiomaUI
    guardar_idioma_ui: GuardarIdiomaUI
    obtener_ruta_guia_sync: ObtenerRutaGuiaSync


class OrquestadorArranqueUI:
    def __init__(self, deps: DependenciasArranque, i18n: I18nManager) -> None:
        self._deps = deps
        self._i18n = i18n

    def resolver_onboarding(self, parent=None) -> bool:
        if self._deps.obtener_estado_onboarding.ejecutar():
            self._i18n.set_idioma(self._deps.obtener_idioma_ui.ejecutar())
            return True

        from presentacion.wizard_bienvenida import WizardBienvenida

        wizard = WizardBienvenida(
            self._i18n,
            self._deps.obtener_ruta_guia_sync,
            idioma_inicial=self._deps.obtener_idioma_ui.ejecutar(),
            pantalla_completa_inicial=self._deps.obtener_preferencia_pantalla_completa.ejecutar(),
            parent=parent,
        )
        if hasattr(wizard, "setModal"):
            wizard.setModal(True)
        if hasattr(wizard, "raise_"):
            wizard.raise_()
        if hasattr(wizard, "activateWindow"):
            wizard.activateWindow()
        if wizard.exec() != WizardBienvenida.Accepted:
            return False

        self._deps.guardar_preferencia_pantalla_completa.ejecutar(wizard.pantalla_completa_por_defecto)
        self._deps.guardar_idioma_ui.ejecutar(wizard.idioma_seleccionado)
        self._deps.marcar_onboarding_completado.ejecutar()
        return True

    def debe_iniciar_maximizada(self) -> bool:
        """Define si la ventana principal debe abrirse maximizada."""
        return self._deps.obtener_preferencia_pantalla_completa.ejecutar()
