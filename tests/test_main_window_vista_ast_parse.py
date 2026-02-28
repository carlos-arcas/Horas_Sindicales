from __future__ import annotations

import ast
from pathlib import Path


def test_main_window_vista_source_parses_on_python_311_plus() -> None:
    source_path = Path("app/ui/vistas/main_window_vista.py")
    source = source_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(source_path))
