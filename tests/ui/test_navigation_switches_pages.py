from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()
QListWidget = qt.QListWidget
QStackedWidget = qt.QStackedWidget
QWidget = qt.QWidget

from app.ui.controladores.controlador_navegacion import ControladorNavegacion


def test_navigation_controller_switches_page() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = QListWidget()
    sidebar.addItem("Uno")
    sidebar.addItem("Dos")
    pages = QStackedWidget()
    pages.addWidget(QWidget())
    pages.addWidget(QWidget())

    controller = ControladorNavegacion(sidebar, pages)
    controller.cambiar_pagina(1)

    assert pages.currentIndex() == 1
    app.processEvents()
