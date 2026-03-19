from __future__ import annotations

import ast
import importlib
from pathlib import Path

PAQUETE_MAIN_WINDOW = (
    Path(__file__).resolve().parents[2] / "app" / "ui" / "vistas" / "main_window"
)
MODULOS_IMPORTACION = (
    "app.ui.vistas.main_window.refresco_mixin",
    "app.ui.vistas.main_window.state_controller",
    "app.ui.vistas.main_window_vista",
)


def test_modulos_main_window_criticos_importan_sin_error() -> None:
    for nombre_modulo in MODULOS_IMPORTACION:
        importlib.import_module(nombre_modulo)


def test_subpaquete_main_window_no_declara_imports_relativos_hacia_modulos_en_padre() -> None:
    incidencias: list[str] = []

    for ruta in sorted(PAQUETE_MAIN_WINDOW.glob("*.py")):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ImportFrom):
                continue
            if nodo.level != 1 or not nodo.module:
                continue

            modulo_relativo = nodo.module.replace(".", "/")
            ruta_local = PAQUETE_MAIN_WINDOW / f"{modulo_relativo}.py"
            paquete_local = PAQUETE_MAIN_WINDOW / modulo_relativo
            if ruta_local.exists() or paquete_local.is_dir():
                continue

            ruta_padre = PAQUETE_MAIN_WINDOW.parent / f"{modulo_relativo}.py"
            if ruta_padre.exists():
                incidencias.append(
                    f"{ruta.relative_to(PAQUETE_MAIN_WINDOW.parents[3])}:{nodo.lineno} "
                    f"usa '.{nodo.module}' pero el módulo real vive en "
                    f"{ruta_padre.relative_to(PAQUETE_MAIN_WINDOW.parents[3])}"
                )

    assert incidencias == [], "\n".join(incidencias)
