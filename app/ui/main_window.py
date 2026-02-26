from __future__ import annotations


def _main_window_real_class():
    from app.ui.vistas.main_window_vista import MainWindow as MainWindowVista

    return MainWindowVista


class MainWindow:
    """Proxy liviano para mantener la API pública estable."""

    def __new__(cls, *args, **kwargs):
        return _main_window_real_class()(*args, **kwargs)


__all__ = ["MainWindow"]
