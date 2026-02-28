from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


RUTA_MAIN_WINDOW = Path("app/ui/vistas/main_window_vista.py")


def test_main_window_vista_no_supera_450_loc() -> None:
    loc = len(RUTA_MAIN_WINDOW.read_text(encoding="utf-8").splitlines())
    assert loc <= 450, f"main_window_vista.py excede límite: {loc} LOC"


def test_main_window_vista_parsea_e_importa() -> None:
    source = RUTA_MAIN_WINDOW.read_text(encoding="utf-8")
    ast.parse(source, filename=str(RUTA_MAIN_WINDOW))

    spec = importlib.util.spec_from_file_location("app.ui.vistas.main_window_vista", RUTA_MAIN_WINDOW)
    assert spec is not None and spec.loader is not None
