from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.ui.estilos.apply_theme import aplicar_tema


def test_aplicar_tema_no_falla() -> None:
    app = QApplication.instance() or QApplication([])
    aplicar_tema(app)
    assert isinstance(app.styleSheet(), str)
