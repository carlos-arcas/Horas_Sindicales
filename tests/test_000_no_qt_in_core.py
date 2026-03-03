from __future__ import annotations

import sys


def test_core_suite_no_importa_pyside6() -> None:
    assert "PySide6" not in sys.modules
    assert not any(name.startswith("PySide6.") for name in sys.modules)
