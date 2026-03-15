from __future__ import annotations

import ast
from pathlib import Path


RUTA_SOLICITUDES = Path("app/application/use_cases/solicitudes")
RUTA_ORQUESTACION_SOLICITUDES = RUTA_SOLICITUDES / "orquestacion_confirmacion.py"
WRAPPERS_PDF_CONFIRMADAS_PROHIBIDOS = {
    "confirmacion_pdf_service.py",
    "pdf_confirmadas_builder.py",
    "pdf_confirmadas_runner.py",
    "servicio_preflight_pdf.py",
}


def test_solicitudes_no_define_wrappers_confirmacion_pdf_legacy() -> None:
    archivos_py = {ruta.name for ruta in RUTA_SOLICITUDES.glob("*.py")}
    assert WRAPPERS_PDF_CONFIRMADAS_PROHIBIDOS.isdisjoint(archivos_py)


def test_orquestacion_confirmacion_no_reexporta_flujo_pdf() -> None:
    arbol = ast.parse(RUTA_ORQUESTACION_SOLICITUDES.read_text(encoding="utf-8"))

    funciones_locales = {
        nodo.name for nodo in arbol.body if isinstance(nodo, ast.FunctionDef)
    }
    assert "confirmar_lote_y_generar_pdf" not in funciones_locales
    assert "generar_pdf_confirmadas" not in funciones_locales

    imports_confirmacion_pdf = {
        nodo.module
        for nodo in arbol.body
        if isinstance(nodo, ast.ImportFrom) and nodo.module
    }
    assert "app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf" not in imports_confirmacion_pdf
