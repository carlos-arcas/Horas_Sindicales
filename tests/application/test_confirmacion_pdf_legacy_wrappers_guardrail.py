from __future__ import annotations

import ast
from pathlib import Path


RUTA_SOLICITUDES_DIR = Path("app/application/use_cases/solicitudes")
RUTA_COMPAT_CONFIRMACION = Path(
    "app/application/use_cases/confirmacion_pdf/orquestacion_compat_solicitudes.py"
)

WRAPPERS_LEGACY_PROHIBIDOS = {
    "servicio_preflight_pdf.py",
    "confirmacion_pdf_service.py",
    "pdf_confirmadas_builder.py",
    "pdf_confirmadas_runner.py",
}


def test_solicitudes_no_contiene_wrappers_legacy_confirmacion_pdf() -> None:
    presentes = {ruta.name for ruta in RUTA_SOLICITUDES_DIR.glob("*.py")}
    assert WRAPPERS_LEGACY_PROHIBIDOS.isdisjoint(presentes)


def test_compat_confirmacion_pdf_expone_superficie_minima() -> None:
    arbol = ast.parse(RUTA_COMPAT_CONFIRMACION.read_text(encoding="utf-8"))
    funciones_publicas = [
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef) and not nodo.name.startswith("_")
    ]

    assert funciones_publicas == [
        "confirmar_solicitudes_lote",
        "resolver_o_crear_solicitud",
    ]

    asignaciones_all = [
        nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in nodo.targets)
    ]
    assert len(asignaciones_all) == 1
