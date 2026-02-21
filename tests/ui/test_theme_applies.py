from __future__ import annotations

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError).QApplication

from app.ui.estilos.apply_theme import aplicar_tema


def test_aplicar_tema_no_falla() -> None:
    app = QApplication.instance() or QApplication([])
    aplicar_tema(app)
    assert isinstance(app.styleSheet(), str)
