from __future__ import annotations

import pytest

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
