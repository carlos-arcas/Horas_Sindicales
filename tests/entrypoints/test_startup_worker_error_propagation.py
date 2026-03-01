from __future__ import annotations

import pytest

from app.entrypoints.arranque_hilo import TrabajadorArranque
from app.entrypoints.ui_main import _manejar_fallo_arranque
from presentacion.i18n import I18nManager


class _I18nDummy:
    def t(self, key: str, **kwargs) -> str:
        textos = {
            "splash_error_mensaje": "Error {incident_id}",
            "splash_error_titulo": "Error inesperado",
            "startup_error_dialog_message": "Fallo al iniciar",
        }
        return textos.get(key, key).format(**kwargs)


class _SplashDummy:
    def request_close(self) -> None:
        return


class _ThreadDummy:
    def quit(self) -> None:
        return


class _DialogDummy:
    def __init__(self, *_args, **_kwargs) -> None:
        return

    def setWindowModality(self, *_args, **_kwargs) -> None:
        return

    def setWindowFlag(self, *_args, **_kwargs) -> None:
        return

    def show(self) -> None:
        return

    def raise_(self) -> None:
        return

    def activateWindow(self) -> None:
        return


class _WatchdogDummy:
    def stop(self) -> None:
        return


def test_worker_exception_propagates_to_ui_and_writes_crash_log(monkeypatch) -> None:
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    if not hasattr(qt_widgets, "QApplication"):
        pytest.skip("Entorno de pruebas sin QApplication real")

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    def _fallar_container():
        raise RuntimeError("boom-propagacion")

    monkeypatch.setattr("app.bootstrap.container.build_container", _fallar_container)

    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    i18n = I18nManager("es")
    worker = TrabajadorArranque(container_seed=None, i18n=i18n)

    errores = []
    worker.error_ocurrido.connect(errores.append)

    worker.run()

    assert len(errores) == 1
    dto = errores[0]

    llamadas_crash = {"calls": 0}

    def _crash_writer(*, tipo_error: str, mensaje_error: str):
        llamadas_crash["calls"] += 1
        assert tipo_error
        assert mensaje_error

    _manejar_fallo_arranque(
        exc=None,
        trace_info=None,
        i18n=_I18nDummy(),
        splash=_SplashDummy(),
        startup_thread=_ThreadDummy(),
        app=app,
        dialogo_factory=_DialogDummy,
        mensaje_usuario=dto.mensaje_usuario,
        incident_id=dto.incident_id,
        detalles=dto.traceback_error,
        watchdog_timer=_WatchdogDummy(),
        crash_log_writer=_crash_writer,
    )

    assert llamadas_crash["calls"] == 1
