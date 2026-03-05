from __future__ import annotations

import pytest


@pytest.fixture
def qt_app():
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    return qt_widgets.QApplication.instance() or qt_widgets.QApplication([])


def test_close_event_tolera_qthread_ya_destruido(qt_app) -> None:
    qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

    from app.ui.splash_window import SplashWindow
    from presentacion.i18n import I18nManager

    splash = SplashWindow(I18nManager("es"))
    hilo = qt_core.QThread(splash)
    splash.registrar_arranque(hilo, qt_core.QObject())
    hilo.deleteLater()
    qt_app.processEvents()

    splash.close()
    qt_app.processEvents()


def test_close_event_programatico_no_toca_thread_invalido(qt_app) -> None:
    qt_gui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

    from app.ui.splash_window import SplashWindow
    from presentacion.i18n import I18nManager

    class _ThreadRoto:
        def isRunning(self) -> bool:
            raise AssertionError("no debe consultar isRunning en cierre programático")

    splash = SplashWindow(I18nManager("es"))
    splash._startup_thread = _ThreadRoto()
    splash.marcar_cierre_programatico()

    evento = qt_gui.QCloseEvent()
    splash.closeEvent(evento)

    assert evento.isAccepted()


def test_close_event_usuario_solicita_cancelacion_una_vez(qt_app) -> None:
    qt_gui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

    from app.ui.splash_window import SplashWindow
    from presentacion.i18n import I18nManager

    class _ThreadActivo:
        def isRunning(self) -> bool:
            return True

    llamadas = {"cancelar": 0}

    splash = SplashWindow(I18nManager("es"))
    splash._startup_thread = _ThreadActivo()
    splash.registrar_cancelacion_arranque(lambda: llamadas.__setitem__("cancelar", llamadas["cancelar"] + 1))

    evento = qt_gui.QCloseEvent()
    splash.closeEvent(evento)

    assert not evento.isAccepted()
    assert llamadas["cancelar"] == 1
