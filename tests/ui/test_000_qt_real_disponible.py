import pytest


qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = qt_widgets.QApplication
QCheckBox = qt_widgets.QCheckBox


def test_qt_real_disponible() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    assert QCheckBox is not None
