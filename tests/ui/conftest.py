import os
import sys
from pathlib import Path

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
    # Este helper es exclusivo de tests UI: evita dependencia accidental en tests no-UI.
    caller_frame = sys._getframe(1)
    caller_file = Path(caller_frame.f_code.co_filename).as_posix()
    if "/tests/ui/" not in f"/{caller_file}":
        raise RuntimeError(
            "require_qt() solo debe usarse desde tests/ui/** para no "
            "acoplar tests no-UI al backend Qt."
        )

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


def _is_ui_item(item: pytest.Item) -> bool:
    """True solo para tests cuyo path real cae dentro de tests/ui/**."""

    item_path = getattr(item, "path", None)
    if item_path is None:
        legacy_path = getattr(item, "fspath", None)
        if legacy_path is None:
            return False
        item_path = Path(str(legacy_path))

    normalized_parts = Path(str(item_path)).as_posix().split("/")
    for idx in range(len(normalized_parts) - 1):
        if normalized_parts[idx] == "tests" and normalized_parts[idx + 1] == "ui":
            return True
    return False


def pytest_collection_modifyitems(config, items):
    qt_ready = _qt_ready()
    smoke_only_in_ci = os.getenv("CI") == "true" and os.getenv("RUN_UI_TESTS") != "1"
    smoke_only_allowlist = {
        "tests/ui/test_ui_arranque_minimo.py",
        "tests/ui/test_ui_navegacion_minima.py",
        "tests/ui/test_ui_headless_fallback_smoke.py",
    }

    skip_non_smoke = pytest.mark.skip(
        reason="Modo smoke en CI: exporta RUN_UI_TESTS=1 para ejecutar toda la suite UI."
    )
    skip_qt = pytest.mark.skip(
        reason="PySide6 no disponible correctamente en entorno CI"
    )

    for item in items:
        if not _is_ui_item(item):
            continue

        item_path = Path(str(getattr(item, "path", ""))).as_posix()
        in_smoke_allowlist = any(item_path.endswith(path) for path in smoke_only_allowlist)
        if smoke_only_in_ci and not in_smoke_allowlist:
            item.add_marker(skip_non_smoke)
            continue

        keywords = getattr(item, "keywords", {})
        if not qt_ready and "headless_safe" not in keywords:
            item.add_marker(skip_qt)
