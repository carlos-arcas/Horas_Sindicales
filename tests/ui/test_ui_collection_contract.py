from __future__ import annotations

import importlib.util

import pytest


def test_ui_collection_contract_no_exit_code_5() -> None:
    """Contrato: este archivo siempre debe coleccionar al menos 1 test en UI."""
    if importlib.util.find_spec("PySide6") is None:
        pytest.skip("PySide6 no disponible en este entorno")

    assert True
