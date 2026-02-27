import inspect
import os
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
    caller_file = Path(inspect.stack()[1].filename).as_posix()
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

    # Explicación breve: solo tocamos tests en tests/ui/** para no skippear
    # accidentalmente tests de dominio/infra cuando Qt no está disponible.
    for item in items:
        if not _is_ui_item(item):
            continue

        if skip_ui_in_ci:
            item.add_marker(skip_in_ci)
            continue

        if not qt_ready:
            item.add_marker(skip_qt)
