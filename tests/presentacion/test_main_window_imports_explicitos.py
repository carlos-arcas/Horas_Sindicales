from __future__ import annotations

import ast
from pathlib import Path

RUTA_APP = Path(__file__).resolve().parents[2] / "app"
RUTA_PAQUETE_MAIN_WINDOW = "app.ui.vistas.main_window"
NOMBRES_REEXPORT_MAGICO = {
    "MainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
    "QMainWindow",
    "HistoricoDetalleDialog",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
}


def _iter_modulos_python_app() -> list[Path]:
    return sorted(RUTA_APP.rglob("*.py"))


def test_app_no_importa_reexports_magicos_desde_paquete_main_window() -> None:
    incidencias: list[str] = []

    for ruta in _iter_modulos_python_app():
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ImportFrom):
                continue
            if nodo.module != RUTA_PAQUETE_MAIN_WINDOW:
                continue
            nombres = {alias.name for alias in nodo.names}
            usados = nombres & NOMBRES_REEXPORT_MAGICO
            if usados:
                usados_texto = ", ".join(sorted(usados))
                incidencias.append(f"{ruta.relative_to(RUTA_APP.parent)} -> {usados_texto}")

    assert incidencias == [], "\n".join(incidencias)
