import os

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
    skip_ui_in_ci = (
        os.getenv("CI") == "true" and os.getenv("RUN_UI_TESTS") != "1"
    )
    qt_ready = _qt_ready()

    skip_in_ci = pytest.mark.skip(
        reason=(
            "UI tests desactivados en CI por defecto "
            "(RUN_UI_TESTS=1 para activarlos)."
        )
    )
    skip_qt = pytest.mark.skip(
        reason="PySide6 no disponible correctamente en entorno CI"
    )

    for item in items:
        nodeid = item.nodeid
        is_ui_path = nodeid.startswith("tests/ui/") or "/tests/ui/" in nodeid
        if not is_ui_path:
            continue

        if skip_ui_in_ci:
            item.add_marker(skip_in_ci)
            continue

        if not qt_ready:
            item.add_marker(skip_qt)
