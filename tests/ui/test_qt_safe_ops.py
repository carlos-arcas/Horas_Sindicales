from __future__ import annotations

from app.ui.qt_safe_ops import es_objeto_qt_valido, safe_hide, safe_quit_thread


class _ObjetoEliminado:
    def __bool__(self) -> bool:
        raise RuntimeError("Internal C++ object already deleted")


class _WidgetFake:
    def __init__(self, *, falla: bool = False) -> None:
        self.hide_calls = 0
        self.close_calls = 0
        self.falla = falla

    def hide(self) -> None:
        self.hide_calls += 1
        if self.falla:
            raise RuntimeError("Internal C++ object (SplashWindow) already deleted")

    def close(self) -> None:
        self.close_calls += 1
        if self.falla:
            raise RuntimeError("Internal C++ object (SplashWindow) already deleted")


class _ThreadFake:
    def __init__(self, *, running: bool, falla_quit: bool = False) -> None:
        self._running = running
        self.quit_calls = 0
        self.falla_quit = falla_quit

    def isRunning(self) -> bool:
        return self._running

    def quit(self) -> None:
        self.quit_calls += 1
        if self.falla_quit:
            raise RuntimeError("Internal C++ object (QThread) already deleted")


def test_es_objeto_qt_valido_tolera_objeto_eliminado() -> None:
    assert es_objeto_qt_valido(_ObjetoEliminado()) is False


def test_safe_hide_es_idempotente_si_widget_ya_fue_eliminado() -> None:
    widget = _WidgetFake(falla=True)

    safe_hide(widget)
    safe_hide(widget)

    assert widget.hide_calls == 2
    assert widget.close_calls == 0


def test_safe_quit_thread_no_hace_nada_si_no_esta_corriendo() -> None:
    thread = _ThreadFake(running=False)

    safe_quit_thread(thread)

    assert thread.quit_calls == 0


def test_safe_quit_thread_tolera_objeto_destruido() -> None:
    thread = _ThreadFake(running=True, falla_quit=True)

    safe_quit_thread(thread)
    safe_quit_thread(thread)

    assert thread.quit_calls == 2
