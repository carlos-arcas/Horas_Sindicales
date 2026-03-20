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
RUTA_ARCHIVO_IMPORTACIONES = RUTA_MAIN_WINDOW / "importaciones.py"
SIMBOLOS_CRITICOS = {
    "GestorToasts",
    "NotificationService",
    "PersonasController",
    "SolicitudesController",
    "SyncController",
    "PdfController",
    "MainWindowHealthMixin",
    "PushWorker",
    "SaldosCard",
    "build_main_window_widgets",
    "build_shell_layout",
    "build_status_bar",
    "run_init_refresh",
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


def test_importaciones_no_reintroduce_fallbacks_genericos_para_criticos() -> None:
    contenido = RUTA_ARCHIVO_IMPORTACIONES.read_text(encoding="utf-8")
    arbol = ast.parse(contenido, filename=str(RUTA_ARCHIVO_IMPORTACIONES))
    fallbacks: dict[str, set[str]] = {}

    for nodo in arbol.body:
        if not isinstance(nodo, ast.Assign):
            continue
        if len(nodo.targets) != 1 or not isinstance(nodo.targets[0], ast.Name):
            continue
        nombre = nodo.targets[0].id
        if nombre not in {"_FALLBACK_GRUPO_DIALOGOS", "_FALLBACK_GRUPO_HELPERS"}:
            continue
        if not isinstance(nodo.value, ast.Dict):
            continue
        claves = {
            clave.value
            for clave in nodo.value.keys
            if isinstance(clave, ast.Constant) and isinstance(clave.value, str)
        }
        fallbacks[nombre] = claves

    for nombre_fallback, claves in fallbacks.items():
        repetidos = sorted(SIMBOLOS_CRITICOS.intersection(claves))
        assert repetidos == [], f"{nombre_fallback} contiene críticos: {', '.join(repetidos)}"
