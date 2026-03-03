from __future__ import annotations

import pytest

pytestmark = pytest.mark.ui

try:
    import PySide6  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Qt no disponible: {exc}", allow_module_level=True)

from presentacion.i18n import I18nManager
from presentacion.orquestador_arranque import DependenciasArranque, OrquestadorArranqueUI


class StubCasoUso:
    def __init__(self, retorno=None) -> None:
        self.retorno = retorno
        self.calls: list[tuple] = []

    def ejecutar(self, *args):
        self.calls.append(args)
        return self.retorno


def _deps(onboarding_completado: bool) -> DependenciasArranque:
    return DependenciasArranque(
        obtener_estado_onboarding=StubCasoUso(onboarding_completado),
        marcar_onboarding_completado=StubCasoUso(),
        guardar_preferencia_pantalla_completa=StubCasoUso(),
        obtener_preferencia_pantalla_completa=StubCasoUso(True),
        obtener_idioma_ui=StubCasoUso("es"),
        guardar_idioma_ui=StubCasoUso(),
        obtener_ruta_guia_sync=StubCasoUso("/tmp/guia.md"),
    )


def test_orquestador_indica_arranque_maximizado_si_preferencia_true() -> None:
    deps = _deps(onboarding_completado=True)
    orquestador = OrquestadorArranqueUI(deps, I18nManager("es"))

    assert orquestador.debe_iniciar_maximizada() is True


def test_orquestador_no_muestra_wizard_si_onboarding_ya_completado() -> None:
    deps = _deps(onboarding_completado=True)
    orquestador = OrquestadorArranqueUI(deps, I18nManager("en"))

    ok = orquestador.resolver_onboarding()

    assert ok is True
    assert deps.obtener_estado_onboarding.calls
    assert deps.obtener_idioma_ui.calls
    assert not deps.guardar_idioma_ui.calls
    assert not deps.marcar_onboarding_completado.calls


def test_orquestador_guarda_onboarding_y_preferencias_al_finalizar(monkeypatch) -> None:
    deps = _deps(onboarding_completado=False)

    class WizardFalso:
        Accepted = 1

        def __init__(self, _i18n, _guia_sync, idioma_inicial, pantalla_completa_inicial, parent=None) -> None:
            self.idioma_seleccionado = "en"
            self.pantalla_completa_por_defecto = not pantalla_completa_inicial
            self.idioma_inicial = idioma_inicial
            self.parent = parent

        def exec(self) -> int:
            return self.Accepted

    monkeypatch.setattr("presentacion.wizard_bienvenida.WizardBienvenida", WizardFalso)
    orquestador = OrquestadorArranqueUI(deps, I18nManager("es"))

    ok = orquestador.resolver_onboarding(parent=object())

    assert ok is True
    assert deps.guardar_preferencia_pantalla_completa.calls == [(False,)]
    assert deps.guardar_idioma_ui.calls == [("en",)]
    assert deps.marcar_onboarding_completado.calls == [()]
