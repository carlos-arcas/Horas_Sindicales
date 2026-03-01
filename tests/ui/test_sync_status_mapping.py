from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path("app/ui/vistas/main_window/sync_status_mapping.py")


def _load_status_to_label():
    spec = importlib.util.spec_from_file_location("sync_status_mapping", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.status_to_label


@pytest.mark.parametrize("status", ["IDLE", "ERROR", "CONFIG_INCOMPLETE"])
def test_status_to_label_known_status_returns_non_empty_str(status: str) -> None:
    status_to_label = _load_status_to_label()
    label = status_to_label(status)
    assert isinstance(label, str)
    assert label.strip() != ""


def test_status_to_label_unknown_status_uses_stable_fallback() -> None:
    status_to_label = _load_status_to_label()
    status = "UNKNOWN"
    assert status_to_label(status) == status
