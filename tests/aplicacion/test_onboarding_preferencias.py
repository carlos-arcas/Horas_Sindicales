from __future__ import annotations

from aplicacion.casos_de_uso.onboarding import (
    MarcarOnboardingCompletado,
    ObtenerEstadoOnboarding,
    ReiniciarOnboarding,
)
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from aplicacion.preferencias_claves import INICIAR_MAXIMIZADA, ONBOARDING_COMPLETADO
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias


class FakeRepositorioPreferencias(IRepositorioPreferencias):
    def __init__(self) -> None:
        self._datos: dict[str, bool] = {}

    def obtener_bool(self, clave: str, por_defecto: bool) -> bool:
        return self._datos.get(clave, por_defecto)

    def guardar_bool(self, clave: str, valor: bool) -> None:
        self._datos[clave] = valor


def test_primera_ejecucion_onboarding_completado_es_false_por_defecto() -> None:
    repositorio = FakeRepositorioPreferencias()
    caso_uso = ObtenerEstadoOnboarding(repositorio)

    assert caso_uso.ejecutar() is False


def test_marcar_onboarding_completado_persiste_true() -> None:
    repositorio = FakeRepositorioPreferencias()
    marcar = MarcarOnboardingCompletado(repositorio)
    obtener_estado = ObtenerEstadoOnboarding(repositorio)

    marcar.ejecutar()

    assert repositorio.obtener_bool(ONBOARDING_COMPLETADO, por_defecto=False) is True
    assert obtener_estado.ejecutar() is True


def test_pantalla_completa_default_false_y_persistencia_true_false() -> None:
    repositorio = FakeRepositorioPreferencias()
    obtener = ObtenerPreferenciaPantallaCompleta(repositorio)
    guardar = GuardarPreferenciaPantallaCompleta(repositorio)

    assert obtener.ejecutar() is False

    guardar.ejecutar(True)
    assert repositorio.obtener_bool(INICIAR_MAXIMIZADA, por_defecto=False) is True
    assert obtener.ejecutar() is True

    guardar.ejecutar(False)
    assert repositorio.obtener_bool(INICIAR_MAXIMIZADA, por_defecto=True) is False
    assert obtener.ejecutar() is False


def test_repositorio_respeta_por_defecto_para_claves_inexistentes() -> None:
    repositorio = FakeRepositorioPreferencias()

    assert repositorio.obtener_bool("clave_no_existente", por_defecto=False) is False
    assert repositorio.obtener_bool("otra_clave_no_existente", por_defecto=True) is True


def test_reiniciar_onboarding_persiste_false() -> None:
    repositorio = FakeRepositorioPreferencias()
    MarcarOnboardingCompletado(repositorio).ejecutar()

    ReiniciarOnboarding(repositorio).ejecutar()

    assert ObtenerEstadoOnboarding(repositorio).ejecutar() is False
