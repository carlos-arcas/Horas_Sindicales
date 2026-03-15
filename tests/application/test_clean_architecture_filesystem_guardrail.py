from __future__ import annotations

import ast
from pathlib import Path

RUTA_APPLICATION = Path("app/application")
RUTA_CONFIRMACION_PDF = Path("app/application/use_cases/confirmacion_pdf")
RUTA_CONTAINER = Path("app/bootstrap/container.py")


def _iter_archivos_python(base: Path) -> list[Path]:
    return sorted(base.rglob("*.py"))


def test_application_no_define_path_file_system() -> None:
    assert not (RUTA_APPLICATION / "use_cases/confirmacion_pdf/path_file_system.py").exists()


def test_application_no_declara_clases_path_file_system() -> None:
    for archivo in _iter_archivos_python(RUTA_APPLICATION):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        clases = [
            nodo.name
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.ClassDef)
        ]
        assert "PathFileSystem" not in clases, str(archivo)


def test_confirmacion_pdf_application_no_importa_fs_concreto() -> None:
    for archivo in _iter_archivos_python(RUTA_CONFIRMACION_PDF):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                assert nodo.module != "app.infrastructure.sistema_archivos.path_file_system", str(archivo)
                assert nodo.module != "app.infrastructure.sistema_archivos.local", str(archivo)


def test_container_wiring_usa_fs_desde_infraestructura() -> None:
    arbol = ast.parse(RUTA_CONTAINER.read_text(encoding="utf-8"))
    imports = {
        nodo.module
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.module
    }
    assert "app.infrastructure.sistema_archivos.local" in imports
