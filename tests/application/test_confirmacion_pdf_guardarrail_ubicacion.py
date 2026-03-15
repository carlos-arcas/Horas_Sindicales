from __future__ import annotations

import ast
from pathlib import Path


RUTA_SOLICITUDES = Path("app/application/use_cases/solicitudes")
RUTA_ORQUESTACION_SOLICITUDES = RUTA_SOLICITUDES / "orquestacion_confirmacion.py"
ARCHIVOS_PDF_CONFIRMADAS_PERMITIDOS = {
    "confirmacion_pdf_service.py",
    "pdf_confirmadas_builder.py",
    "pdf_confirmadas_runner.py",
}


def test_solicitudes_no_define_nuevos_modulos_pdf_confirmadas() -> None:
    archivos_pdf = {
        ruta.name
        for ruta in RUTA_SOLICITUDES.glob("*pdf*confirmad*.py")
    }
    assert archivos_pdf <= ARCHIVOS_PDF_CONFIRMADAS_PERMITIDOS


def test_orquestacion_confirmacion_delega_flujo_pdf_al_bounded_context() -> None:
    arbol = ast.parse(RUTA_ORQUESTACION_SOLICITUDES.read_text(encoding="utf-8"))

    funciones_locales = {
        nodo.name for nodo in arbol.body if isinstance(nodo, ast.FunctionDef)
    }
    assert "confirmar_lote_y_generar_pdf" not in funciones_locales
    assert "generar_pdf_confirmadas" not in funciones_locales

    imports_origen_pdf = {
        alias.name
        for nodo in arbol.body
        if isinstance(nodo, ast.ImportFrom)
        and nodo.module
        == "app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf"
        for alias in nodo.names
    }
    assert "confirmar_lote_y_generar_pdf" in imports_origen_pdf
    assert "generar_pdf_confirmadas" in imports_origen_pdf
