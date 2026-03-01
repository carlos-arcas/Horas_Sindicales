from __future__ import annotations

import pytest

class _I18nDummy:
    def t(self, key: str, **kwargs) -> str:
        return key


class _SplashDummy:
    def __init__(self, widget) -> None:
        self._widget = widget
        self.close_calls = 0

    def request_close(self) -> None:
        self.close_calls += 1
        self._widget.hide()
        self._widget.close()

    def set_status(self, _etapa: str) -> None:
        return

    def hide(self) -> None:
        self._widget.hide()

    def close(self) -> None:
        self._widget.close()

    def isVisible(self) -> bool:
        return self._widget.isVisible()


def _no_op(**_kwargs):
    return ""


def test_on_timeout_cierra_splash_de_forma_idempotente() -> None:
    try:
        from PySide6.QtCore import QThread, QTimer
        from PySide6.QtWidgets import QApplication, QWidget
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Qt no disponible en entorno de test: {exc}")

    from app.entrypoints.coordinador_arranque import CoordinadorArranque

    app = QApplication.instance() or QApplication([])
    splash_widget = QWidget()
    splash = _SplashDummy(splash_widget)
    splash_widget.show()
    thread = QThread()
    watchdog = QTimer()
    watchdog.setSingleShot(True)

    coordinador = CoordinadorArranque(
        app=app,
        i18n=_I18nDummy(),
        splash=splash,
        startup_timeout_ms=10,
        startup_thread=thread,
        startup_worker=object(),
        watchdog_timer=watchdog,
        main_window_factory=lambda *_args, **_kwargs: object(),
        orquestador_factory=lambda *_args, **_kwargs: object(),
        instalar_menu_ayuda=lambda *_args, **_kwargs: None,
        fallo_arranque_handler=_no_op,
    )

    coordinador.on_timeout()
    coordinador.on_timeout()

    assert splash.close_calls == 1
    assert not splash.isVisible()
