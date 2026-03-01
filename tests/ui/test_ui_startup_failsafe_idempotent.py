from __future__ import annotations

from app.entrypoints import ui_main


class _ObjetoRuntimeError:
    def __bool__(self) -> bool:
        raise RuntimeError("Internal C++ object already deleted")


class _SplashInestable:
    def __init__(self) -> None:
        self.hide_calls = 0
        self.close_calls = 0

    def hide(self) -> None:
        self.hide_calls += 1
        raise RuntimeError("Internal C++ object (SplashWindow) already deleted")

    def close(self) -> None:
        self.close_calls += 1
        raise RuntimeError("Internal C++ object (SplashWindow) already deleted")


def test_es_objeto_qt_valido_devuelve_false_si_objeto_invalido() -> None:
    assert ui_main._es_objeto_qt_valido(_ObjetoRuntimeError()) is False


def test_cerrar_splash_seguro_es_idempotente_ante_runtime_error() -> None:
    splash = _SplashInestable()

    ui_main._cerrar_splash_seguro(splash)
    ui_main._cerrar_splash_seguro(splash)

    assert splash.hide_calls == 2
    assert splash.close_calls == 0
