from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_root_conftest_module():
    module_path = Path(__file__).resolve().parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("root_conftest_qtbot", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyItem:
    def __init__(self, nodeid: str, *, fixturenames: tuple[str, ...] = (), ui: bool = False) -> None:
        self.nodeid = nodeid
        self.fixturenames = fixturenames
        self.keywords = {"ui": True} if ui else {}
        self.markers: list[object] = []

    def add_marker(self, marker: object) -> None:
        self.markers.append(marker)

    def get_closest_marker(self, name: str):
        if name in self.keywords:
            return object()
        return None


class _DummyConfig:
    def __init__(self) -> None:
        self.option = SimpleNamespace(markexpr="")
        self.args: list[str] = ["tests/ui"]


def test_qtbot_opcional_se_skippea_si_falta_pytest_qt(monkeypatch) -> None:
    root_conftest = _load_root_conftest_module()
    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "0")
    monkeypatch.setattr(root_conftest, "detectar_error_qt", lambda: None)
    monkeypatch.setattr(root_conftest, "detectar_error_pytest_qt", lambda: "pytest-qt ausente")
    monkeypatch.setattr(root_conftest, "_PYTEST_QT_ERROR", None)
    monkeypatch.setattr(root_conftest, "_UI_BACKEND_ERROR", None)

    item = _DummyItem("tests/ui/test_toast_system_smoke.py::test_emitir", fixturenames=("qtbot",), ui=True)

    root_conftest.pytest_collection_modifyitems(_DummyConfig(), [item])

    assert item.markers, "Debe marcarse skip cuando falta pytest-qt y el test usa qtbot"
    assert any("pytest-qt ausente" in str(marker) for marker in item.markers)


def test_smoke_estricto_con_qtbot_falla_claro_si_falta_pytest_qt(monkeypatch) -> None:
    root_conftest = _load_root_conftest_module()
    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "1")
    monkeypatch.setattr(root_conftest, "detectar_error_pytest_qt", lambda: "pytest-qt ausente")

    item = _DummyItem(
        "tests/ui/test_confirmar_pdf_mainwindow_smoke.py::test_smoke",
        fixturenames=("qtbot",),
        ui=True,
    )

    with pytest.raises(RuntimeError, match="pytest-qt/qtbot"):
        root_conftest.pytest_runtest_setup(item)
