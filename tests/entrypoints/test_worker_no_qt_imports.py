from __future__ import annotations

from pathlib import Path


def test_arranque_nucleo_no_referencia_pyside() -> None:
    source = Path("app/entrypoints/arranque_nucleo.py").read_text(encoding="utf-8")

    assert "PySide6" not in source
    assert "QApplication" not in source
    assert "QTimer" not in source
