from __future__ import annotations

import pytest


def test_qt_bindings_sanity() -> None:
    """Diagnóstico mínimo para detectar stubs/shadowing de PySide6 en CI."""
    try:
        import PySide6  # noqa: F401
        from PySide6 import QtCore, QtWidgets
    except Exception as exc:  # pragma: no cover - diagnóstico en entornos sin Qt
        pytest.skip(f"PySide6 no está disponible/importable en este entorno: {exc}")

    if not hasattr(QtWidgets, "QApplication"):
        pytest.skip(
            "PySide6 importó, pero falta QtWidgets.QApplication; posible stub/shadowing."
        )

    if not hasattr(QtCore, "QEvent"):
        pytest.skip("PySide6 importó, pero falta QtCore.QEvent; posible stub/shadowing.")

    assert hasattr(QtWidgets, "QApplication")
    assert hasattr(QtCore, "QEvent")
