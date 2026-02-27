from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_ui_conftest_module():
    module_path = Path(__file__).resolve().parent / "ui" / "conftest.py"
    spec = importlib.util.spec_from_file_location("ui_conftest_scope", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyItem:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.markers: list[object] = []

    def add_marker(self, marker: object) -> None:
        self.markers.append(marker)


def test_pytest_collection_modifyitems_only_skips_ui_items(monkeypatch) -> None:
    ui_conftest = _load_ui_conftest_module()
    monkeypatch.setattr(ui_conftest, "_qt_ready", lambda: False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("RUN_UI_TESTS", raising=False)

    ui_item = _DummyItem("tests/ui/test_algo_ui.py")
    non_ui_item = _DummyItem("tests/domain/test_algo.py")

    ui_conftest.pytest_collection_modifyitems(None, [ui_item, non_ui_item])

    assert ui_item.markers, "El test UI debe marcarse skip sin Qt"
    assert not non_ui_item.markers, "Un test fuera de tests/ui no debe skippearse"
