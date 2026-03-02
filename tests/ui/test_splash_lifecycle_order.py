from __future__ import annotations

import builtins
import sys
from types import SimpleNamespace

import pytest

from app.entrypoints import ui_main
from app.entrypoints.arranque_nucleo import ResultadoArranque

pytestmark = pytest.mark.headless_safe


class FakeSplash:
    def __init__(self, *, fail=False, events=None) -> None:
        self.hide_called = 0
        self.close_called = 0
        self.fail = fail
        self.events = events if events is not None else []

    def hide(self) -> None:
        self.hide_called += 1
        self.events.append("splash_hide")
        if self.fail:
            raise RuntimeError("deleted")

    def close(self) -> None:
        self.close_called += 1
        self.events.append("splash_close")
        if self.fail:
            raise RuntimeError("deleted")


class FakeTimer:
    def __init__(self, events=None) -> None:
        self.stop_called = 0
        self.events = events if events is not None else []

    def stop(self) -> None:
        self.stop_called += 1
        self.events.append("watchdog_stop")


class _CoordinatorFake(ui_main._CoordinadorArranqueConCierreDeterminista):
    def __init__(self, *, splash, timer, events) -> None:
        self.splash = splash
        self.watchdog_timer = timer
        self.events = events
        self._splash_cerrado = False
        self.terminado = False
        self.thread = object()
        self.i18n = SimpleNamespace(
            set_idioma=lambda _idioma: events.append("set_idioma")
        )
        self.app = SimpleNamespace(
            exit=lambda _code: events.append("app_exit"), setProperty=lambda *_: None
        )
        self.orquestador_factory = lambda _deps, _i18n: SimpleNamespace(
            resolver_onboarding=lambda: events.append("wizard") or True,
            debe_iniciar_maximizada=lambda: False,
        )
        self.main_window_factory = lambda _container, _deps: events.append(
            "main_window"
        ) or SimpleNamespace(show=lambda: None)
        self.instalar_menu_ayuda = lambda *_args, **_kwargs: events.append("menu")
        self._reportar_fallo_arranque = lambda **_kwargs: events.append("error")

    def _qt_is_alive(self, _obj) -> bool:
        return True

    def _solicitar_cierre_thread(self) -> None:
        self.events.append("thread_quit")


def test_on_finished_cierra_splash_antes_de_wizard_y_main(monkeypatch) -> None:
    qtimer_fake = SimpleNamespace(singleShot=lambda _ms, fn: fn())
    monkeypatch.setitem(
        sys.modules, "PySide6.QtCore", SimpleNamespace(QTimer=qtimer_fake)
    )

    events: list[str] = []
    splash = FakeSplash(events=events)
    timer = FakeTimer(events=events)
    coord = _CoordinatorFake(splash=splash, timer=timer, events=events)
    monkeypatch.setattr(ui_main, "ReiniciarOnboarding", lambda _repo: object())

    deps_arranque = SimpleNamespace(
        obtener_idioma_ui=SimpleNamespace(ejecutar=lambda: "es"),
    )
    payload = ResultadoArranque(
        container=SimpleNamespace(
            repositorio_preferencias=None, cargar_datos_demo_caso_uso=None
        ),
        deps_arranque=deps_arranque,
        idioma="es",
    )
    coord.on_finished(payload)

    assert "wizard" in events and "main_window" in events
    assert events.index("splash_hide") < events.index("wizard")
    assert events.index("splash_hide") < events.index("main_window")


def test_cerrar_splash_seguro_es_idempotente_y_tolera_runtime_error() -> None:
    splash = FakeSplash()
    ui_main._cerrar_splash_seguro(splash)
    ui_main._cerrar_splash_seguro(splash)

    assert splash.hide_called == 2
    assert splash.close_called == 2

    roto = FakeSplash(fail=True)
    ui_main._cerrar_splash_seguro(roto)
    ui_main._cerrar_splash_seguro(roto)


def test_stop_watchdog_en_main_thread_usa_singleshot_si_hay_qtimer(monkeypatch) -> None:
    eventos: list[str] = []
    timer = FakeTimer(events=eventos)

    class _QTimerFake:
        @staticmethod
        def singleShot(_delay, callback):
            eventos.append("single_shot")
            callback()

    original_import = builtins.__import__

    def _import_hook(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PySide6.QtCore":
            return SimpleNamespace(QTimer=_QTimerFake)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import_hook)

    ui_main._stop_watchdog_en_main_thread(timer)

    assert eventos == ["single_shot", "watchdog_stop"]
