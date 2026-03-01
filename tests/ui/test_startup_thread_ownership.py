from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.entrypoints import ui_main


@pytest.fixture
def qt_available():
    pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)


@dataclass
class _DummyUseCase:
    def ejecutar(self):
        return "es"


@dataclass
class _DummyDeps:
    obtener_idioma_ui: _DummyUseCase
    guardar_preferencia_pantalla_completa: object = None
    obtener_preferencia_pantalla_completa: object = None


class _DummyOrquestador:
    def __init__(self, _deps, _i18n) -> None:
        pass

    def resolver_onboarding(self) -> bool:
        return True

    def debe_iniciar_maximizada(self) -> bool:
        return False


class _DialogSpy:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def setWindowModality(self, *_args, **_kwargs) -> None:
        return None

    def setWindowFlag(self, *_args, **_kwargs) -> None:
        return None

    def show(self) -> None:
        return None

    def raise_(self) -> None:
        return None

    def activateWindow(self) -> None:
        return None


class _MainWindowRoto:
    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError("fallo intencional creando MainWindow")


class _DummyContainer:
    persona_use_cases = None
    solicitud_use_cases = None
    grupo_use_cases = None
    sheets_service = None
    sync_service = None
    conflicts_service = None
    health_check_use_case = None
    alert_engine = None
    validacion_preventiva_lock_use_case = None
    repositorio_preferencias = None
    cargar_datos_demo_caso_uso = None


def test_manejar_fallo_arranque_es_idempotente_y_seguro(monkeypatch, qt_available) -> None:
    from PySide6.QtWidgets import QApplication

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    class _I18nDummy:
        def t(self, key: str, **kwargs) -> str:
            valores = {
                "splash_error_mensaje": "Error {incident_id}",
                "splash_error_titulo": "Error inesperado",
                "startup_error_dialog_message": "Ha ocurrido un error inesperado.",
            }
            return valores.get(key, key).format(**kwargs)

    class _SplashDummy:
        request_close_calls = 0

        def request_close(self) -> None:
            self.request_close_calls += 1

    class _ThreadDummy:
        quit_calls = 0

        def quit(self) -> None:
            self.quit_calls += 1

    class _WatchdogDummy:
        stop_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

    app = QApplication.instance() or QApplication([])
    if hasattr(app, "_fallo_arranque_reportado"):
        delattr(app, "_fallo_arranque_reportado")
    splash = _SplashDummy()
    startup_thread = _ThreadDummy()
    watchdog = _WatchdogDummy()

    ui_main._manejar_fallo_arranque(
        exc=RuntimeError("boom"),
        trace_info=None,
        i18n=_I18nDummy(),
        splash=splash,
        startup_thread=startup_thread,
        app=app,
        dialogo_factory=_DialogSpy,
        watchdog_timer=watchdog,
    )
    ui_main._manejar_fallo_arranque(
        exc=RuntimeError("boom-2"),
        trace_info=None,
        i18n=_I18nDummy(),
        splash=splash,
        startup_thread=startup_thread,
        app=app,
        dialogo_factory=_DialogSpy,
        watchdog_timer=watchdog,
    )

    assert splash.request_close_calls == 1
    assert startup_thread.quit_calls == 1
    assert watchdog.stop_calls == 1


def test_fallo_en_mainwindow_cierra_splash_y_no_wait(monkeypatch, qt_available) -> None:
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    request_close_calls = {"calls": 0}
    wait_calls = {"calls": 0}

    real_request_close = pytest.importorskip("app.ui.splash_window", exc_type=ImportError).SplashWindow.request_close

    def _request_close_spy(self):
        request_close_calls["calls"] += 1
        return real_request_close(self)

    def _wait_spy(*_args, **_kwargs):
        wait_calls["calls"] += 1
        raise AssertionError("QThread.wait no debe invocarse")

    monkeypatch.setattr("app.ui.splash_window.SplashWindow.request_close", _request_close_spy)
    monkeypatch.setattr(qt_core.QThread, "wait", _wait_spy, raising=False)
    monkeypatch.setattr("presentacion.orquestador_arranque.OrquestadorArranqueUI", _DummyOrquestador)
    monkeypatch.setattr("app.ui.main_window.MainWindow", _MainWindowRoto)
    monkeypatch.setattr(
        ui_main,
        "_construir_dependencias_arranque",
        lambda _container: _DummyDeps(obtener_idioma_ui=_DummyUseCase()),
    )
    monkeypatch.setattr("app.ui.dialogos.dialogo_error_arranque.DialogoErrorArranque", _DialogSpy)

    exit_code = ui_main.run_ui(container=_DummyContainer())

    assert exit_code == 2
    assert request_close_calls["calls"] >= 1
    assert wait_calls["calls"] == 0
