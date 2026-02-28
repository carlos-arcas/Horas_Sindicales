from __future__ import annotations

from pathlib import Path


def test_main_window_init_is_thin() -> None:
    init_path = Path("app/ui/vistas/main_window/__init__.py")
    lines = init_path.read_text(encoding="utf-8").splitlines()
    loc = len(lines)
    assert loc <= 50, f"__init__.py excede 50 LOC: {loc}"

    content = "\n".join(lines)
    assert "class MainWindow" not in content
    assert content.count("def ") <= 3


def test_modulo_implementacion_declara_mainwindow() -> None:
    modulo = Path("app/ui/vistas/main_window/state_controller.py")
    assert modulo.exists(), "Debe existir el módulo de implementación"
    content = modulo.read_text(encoding="utf-8")
    assert "class MainWindow" in content
