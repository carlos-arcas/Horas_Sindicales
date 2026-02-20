from __future__ import annotations

from pathlib import Path


def test_use_cases_init_is_thin() -> None:
    init_file = Path("app/application/use_cases/__init__.py")
    source = init_file.read_text(encoding="utf-8")
    lines = source.splitlines()

    assert len(lines) <= 200, "use_cases/__init__.py debe permanecer delgado (<=200 líneas)."

    stripped = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    class_defs = [line for line in stripped if line.startswith("class ")]
    assert not class_defs, "use_cases/__init__.py no debe definir clases, solo reexports." 

    func_defs = [line for line in stripped if line.startswith("def ")]
    assert not func_defs, "use_cases/__init__.py no debe contener lógica de funciones."


def test_use_cases_init_no_infra_imports() -> None:
    init_file = Path("app/application/use_cases/__init__.py")
    source = init_file.read_text(encoding="utf-8")
    assert "app.infrastructure" not in source
