from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.entrypoints import ui_main


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
    invocaciones: list[dict[str, str]] = []

    def __init__(
        self,
        _i18n,
        *,
        titulo: str,
        mensaje_usuario: str,
        incident_id: str,
        detalles: str | None = None,
        parent=None,
    ) -> None:
        self.__class__.invocaciones.append(
            {
                "titulo": titulo,
                "mensaje_usuario": mensaje_usuario,
                "incident_id": incident_id,
                "detalles": detalles or "",
            }
        )
        self._parent = parent

    def exec(self) -> int:
        return 0


class _MainWindowRoto:
    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError("fallo intencional creando MainWindow")


def test_startup_failsafe_muestra_dialogo_con_incident_id_y_quit_thread(monkeypatch) -> None:
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    if not hasattr(qt_core, "QThread"):
        pytest.skip("PySide6.QtCore sin QThread")

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _DialogSpy.invocaciones.clear()

    quit_spy = {"calls": 0}
    qthread_quit = qt_core.QThread.quit

    def _quit_with_spy(self):
        quit_spy["calls"] += 1
        return qthread_quit(self)

    monkeypatch.setattr(qt_core.QThread, "quit", _quit_with_spy, raising=False)
    monkeypatch.setattr("presentacion.orquestador_arranque.OrquestadorArranqueUI", _DummyOrquestador)
    monkeypatch.setattr("app.ui.main_window.MainWindow", _MainWindowRoto)
    monkeypatch.setattr(
        ui_main,
        "_construir_dependencias_arranque",
        lambda _container: _DummyDeps(obtener_idioma_ui=_DummyUseCase()),
    )
    monkeypatch.setattr("app.ui.dialogos.dialogo_error_arranque.DialogoErrorArranque", _DialogSpy)

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

    exit_code = ui_main.run_ui(container=_DummyContainer())

    assert exit_code == 2
    assert _DialogSpy.invocaciones
    assert _DialogSpy.invocaciones[-1]["incident_id"]
    assert quit_spy["calls"] >= 1


def test_startup_watchdog_timeout_muestra_dialogo_y_no_wait(monkeypatch) -> None:
    pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("HORAS_STARTUP_TIMEOUT_MS", "100")
    _DialogSpy.invocaciones.clear()

    wait_calls = {"calls": 0}

    def _wait_spy(*_args, **_kwargs):
        wait_calls["calls"] += 1
        raise AssertionError("QThread.wait no debe invocarse")

    monkeypatch.setattr("PySide6.QtCore.QThread.wait", _wait_spy, raising=False)

    def _run_colgado(_self) -> None:
        from PySide6.QtCore import QThread

        QThread.msleep(400)

    monkeypatch.setattr("app.entrypoints.arranque_hilo.TrabajadorArranque.run", _run_colgado, raising=False)
    monkeypatch.setattr("app.ui.dialogos.dialogo_error_arranque.DialogoErrorArranque", _DialogSpy)

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

    exit_code = ui_main.run_ui(container=_DummyContainer())

    assert exit_code == 2
    assert _DialogSpy.invocaciones
    assert _DialogSpy.invocaciones[-1]["mensaje_usuario"]
    assert wait_calls["calls"] == 0


def test_manejar_fallo_arranque_difiere_exit_hasta_cerrar_dialogo(monkeypatch, qtbot) -> None:
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
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
        def hide(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _ThreadDummy:
        quit_calls = 0

        def quit(self) -> None:
            self.quit_calls += 1

    class _WatchdogDummy:
        stop_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

    class _DialogControl(qt_widgets.QDialog):
        last = None

        def __init__(self, _i18n, **_kwargs) -> None:
            super().__init__(None)
            self.__class__.last = self

    exit_codes: list[int] = []
    real_exit = qt_widgets.QApplication.exit

    def _exit_spy(code: int = 0) -> None:
        exit_codes.append(code)

    monkeypatch.setattr(qt_widgets.QApplication, "exit", _exit_spy)

    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    thread = _ThreadDummy()
    watchdog = _WatchdogDummy()

    ui_main._manejar_fallo_arranque(
        exc=RuntimeError("boom"),
        trace_info=None,
        i18n=_I18nDummy(),
        splash=_SplashDummy(),
        startup_thread=thread,
        app=app,
        dialogo_factory=_DialogControl,
        watchdog_timer=watchdog,
    )

    assert _DialogControl.last is not None
    assert exit_codes == []

    qtbot.addWidget(_DialogControl.last)
    qt_core.QTimer.singleShot(0, _DialogControl.last.accept)
    qtbot.waitUntil(lambda: exit_codes == [2], timeout=1000)
    assert thread.quit_calls == 1
    assert watchdog.stop_calls == 1

    monkeypatch.setattr(qt_widgets.QApplication, "exit", real_exit)
