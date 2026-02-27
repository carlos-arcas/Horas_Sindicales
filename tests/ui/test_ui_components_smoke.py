from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

QApplication = require_qt()
QWidget = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError).QWidget

from app.ui.components.saldos_card import SaldosCard
from app.ui.components.secondary_button import SecondaryButton


def test_secondary_button_can_be_created() -> None:
    app = QApplication.instance() or QApplication([])
    button = SecondaryButton("Acción")
    assert button.text() == "Acción"
    button.deleteLater()
    app.processEvents()


def test_saldos_card_is_qwidget() -> None:
    app = QApplication.instance() or QApplication([])
    card = SaldosCard()
    assert isinstance(card, QWidget)
    card.deleteLater()
    app.processEvents()
