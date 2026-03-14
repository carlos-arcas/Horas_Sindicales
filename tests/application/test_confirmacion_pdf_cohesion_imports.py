from __future__ import annotations

import ast
from pathlib import Path


RUTA_CASO_USO = Path("app/application/use_cases/confirmacion_pdf/generar_pdf_confirmadas_caso_uso.py")


def _imports_desde_modulo(path_archivo: Path) -> set[str]:
    arbol = ast.parse(path_archivo.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            imports.add(nodo.module)
    return imports


def test_generar_pdf_confirmadas_no_depende_de_modulos_solicitudes_pdf() -> None:
    imports = _imports_desde_modulo(RUTA_CASO_USO)

    assert "app.application.use_cases.solicitudes.confirmacion_pdf_service" not in imports
    assert "app.application.use_cases.solicitudes.orquestacion_confirmacion" not in imports
    assert "app.application.use_cases.solicitudes.pdf_confirmadas_builder" not in imports
    assert "app.application.use_cases.solicitudes.pdf_confirmadas_runner" not in imports


def test_generar_pdf_confirmadas_depende_de_contexto_confirmacion_pdf() -> None:
    imports = _imports_desde_modulo(RUTA_CASO_USO)

    assert "app.application.use_cases.confirmacion_pdf.orquestacion_pdf_confirmadas" in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder" in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner" in imports
    assert "app.application.use_cases.confirmacion_pdf.servicio_pdf_confirmadas" in imports
