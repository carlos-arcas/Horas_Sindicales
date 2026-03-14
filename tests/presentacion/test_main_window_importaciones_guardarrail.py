from __future__ import annotations

import ast
from pathlib import Path

RUTA_MAIN_WINDOW = (
    Path(__file__).resolve().parents[2] / "app" / "ui" / "vistas" / "main_window"
)
RUTA_IMPORTACIONES = "app.ui.vistas.main_window.importaciones"
ARCHIVOS_PERMITIDOS = {
    "importaciones.py",
    "state_controller.py",
}


def test_consumidores_internos_no_importan_aliases_planos_desde_importaciones() -> None:
    incidencias: list[str] = []

    for ruta in sorted(RUTA_MAIN_WINDOW.glob("*.py")):
        if ruta.name in ARCHIVOS_PERMITIDOS:
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ImportFrom):
                continue
            if nodo.module != RUTA_IMPORTACIONES:
                continue
            nombres = ", ".join(alias.name for alias in nodo.names)
            incidencias.append(
                f"{ruta.relative_to(RUTA_MAIN_WINDOW.parent.parent.parent)} -> {nombres}"
            )

    assert incidencias == [], "\n".join(incidencias)
