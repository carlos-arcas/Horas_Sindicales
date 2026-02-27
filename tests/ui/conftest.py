import pytest


def _qt_ready() -> bool:
    try:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication

        _ = (QApplication, QEvent)
        return True
    except Exception:
        return False


def require_qt():
    try:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication

        _ = QEvent
        return QApplication
    except Exception:
        pytest.skip(
            "PySide6 no disponible correctamente en entorno CI",
            allow_module_level=True,
        )


def pytest_collection_modifyitems(config, items):
    if _qt_ready():
        return

    skip_qt = pytest.mark.skip(reason="PySide6 no disponible correctamente en entorno CI")
    for item in items:
        nodeid = item.nodeid
        is_ui_path = nodeid.startswith("tests/ui/") or "/tests/ui/" in nodeid
        has_ui_marker = item.get_closest_marker("qt") or item.get_closest_marker("ui")

        if is_ui_path or has_ui_marker:
            item.add_marker(skip_qt)
