from __future__ import annotations

import pytest


def test_splash_window_smoke_muestra_estado_cargando() -> None:
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    for required in ("QApplication", "QLabel", "QProgressBar"):
        if not hasattr(qt_widgets, required):
            pytest.skip(f"PySide6.QtWidgets sin {required} en este entorno")

    from app.ui.splash_window import SplashWindow
    from presentacion.i18n import I18nManager

    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])

    splash = SplashWindow(I18nManager("es"))
    splash.show()
    app.processEvents()

    labels = [label.text() for label in splash.findChildren(qt_widgets.QLabel)]
    assert any("Cargando" in text for text in labels)

    progress_bars = splash.findChildren(qt_widgets.QProgressBar)
    assert len(progress_bars) == 1
    assert progress_bars[0].minimum() == 0
    assert progress_bars[0].maximum() == 0

    splash.close()
