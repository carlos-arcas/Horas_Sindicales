from __future__ import annotations

import pytest

from app.entrypoints import ui_main


class _I18nDummy:
    def t(self, key: str, **kwargs) -> str:
        textos = {
            "splash_error_mensaje": "Error {incident_id}",
            "splash_error_titulo": "Error inesperado",
            "startup_error_dialog_message": "Fallo al iniciar",
        }
        return textos.get(key, key).format(**kwargs)


class _DeletedSplash:
    def hide(self) -> None:
        raise RuntimeError("Internal C++ object (SplashWindow) already deleted")

    def close(self) -> None:
        raise RuntimeError("Internal C++ object (SplashWindow) already deleted")


class _DeletedThread:
    def quit(self) -> None:
        raise RuntimeError("Internal C++ object (PySide6.QtCore.QThread) already deleted")


class _DeletedWatchdog:
    def stop(self) -> None:
        raise RuntimeError("Internal C++ object already deleted")


class _DialogSpy:
    calls = 0

    def __init__(self, *_args, **_kwargs) -> None:
        self.__class__.calls += 1

    def exec(self) -> int:
        return 0


def test_manejar_fallo_arranque_tolera_objetos_qt_eliminados_y_no_usa_wait(monkeypatch) -> None:
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    wait_calls = {"calls": 0}

    def _wait_spy(*_args, **_kwargs):
        wait_calls["calls"] += 1
        raise AssertionError("QThread.wait no debe llamarse en fail-safe")

    monkeypatch.setattr(qt_core.QThread, "wait", _wait_spy, raising=False)

    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    _DialogSpy.calls = 0

    incident_id = ui_main._manejar_fallo_arranque(
        exc=RuntimeError("boom"),
        trace_info=None,
        i18n=_I18nDummy(),
        splash=_DeletedSplash(),
        startup_thread=_DeletedThread(),
        app=app,
        dialogo_factory=_DialogSpy,
        watchdog_timer=_DeletedWatchdog(),
    )

    second_incident_id = ui_main._manejar_fallo_arranque(
        exc=RuntimeError("boom 2"),
        trace_info=None,
        i18n=_I18nDummy(),
        splash=_DeletedSplash(),
        startup_thread=_DeletedThread(),
        app=app,
        dialogo_factory=_DialogSpy,
        watchdog_timer=_DeletedWatchdog(),
    )

    assert incident_id
    assert second_incident_id == incident_id
    assert _DialogSpy.calls == 1
    assert wait_calls["calls"] == 0
