from __future__ import annotations

from app.entrypoints.arranque_nucleo import ResultadoArranqueCore, planificar_arranque_core


class _ContainerDummy:
    pass


def test_planificar_arranque_core_reutiliza_container_seed() -> None:
    container = _ContainerDummy()

    resultado = planificar_arranque_core(container)

    assert isinstance(resultado, ResultadoArranqueCore)
    assert resultado.container is container


def test_planificar_arranque_core_construye_container_headless(monkeypatch) -> None:
    esperado = _ContainerDummy()
    llamadas = {"preferencias_headless": None}

    def _build_container(*, preferencias_headless: bool):
        llamadas["preferencias_headless"] = preferencias_headless
        return esperado

    monkeypatch.setattr("app.bootstrap.container.build_container", _build_container)

    resultado = planificar_arranque_core(None)

    assert resultado.container is esperado
    assert llamadas["preferencias_headless"] is True
