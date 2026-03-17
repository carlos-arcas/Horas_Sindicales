from __future__ import annotations

import ast
from pathlib import Path


RUTA_SOLICITUDES = Path("app/application/use_cases/solicitudes")
RUTA_ORQUESTACION_SOLICITUDES = RUTA_SOLICITUDES / "orquestacion_confirmacion.py"
RUTA_SERVICIO_PREFLIGHT = Path(
    "app/application/use_cases/confirmacion_pdf/servicio_preflight_pdf.py"
)
RUTA_SERVICIO_DESTINO = Path(
    "app/application/use_cases/confirmacion_pdf/servicio_destino_pdf_confirmacion.py"
)
RUTA_TESTS_SOLICITUDES = Path("tests/application/use_cases/solicitudes")
HELPERS_DESTINO_PROHIBIDOS = {
    "NOMBRE_PDF_POR_DEFECTO",
    "ResolucionDestinoPdf",
    "resolver_destino_pdf",
    "resolver_colision_pdf",
    "resolver_ruta_sin_colision",
}

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


def test_servicios_confirmacion_pdf_tienen_modulos_dedicados() -> None:
    modulo_preflight = RUTA_SERVICIO_PREFLIGHT.read_text(encoding="utf-8")
    modulo_destino = RUTA_SERVICIO_DESTINO.read_text(encoding="utf-8")

    assert "class ServicioPreflightPdf" in modulo_preflight
    assert "class ServicioDestinoPdfConfirmacion" not in modulo_preflight

    assert "class ServicioDestinoPdfConfirmacion" in modulo_destino
    assert "class ServicioPreflightPdf" not in modulo_destino


def test_tests_confirmacion_pdf_no_quedan_en_namespace_solicitudes() -> None:
    for ruta_test in RUTA_TESTS_SOLICITUDES.glob("test_*.py"):
        contenido = ruta_test.read_text(encoding="utf-8")
        assert "use_cases.confirmacion_pdf" not in contenido, (
            "Mover tests de confirmacion_pdf fuera de solicitudes: "
            f"{ruta_test}"
        )


def test_confirmacion_pdf_no_importa_helpers_destino_desde_solicitudes() -> None:
    for ruta_modulo in Path("app/application/use_cases/confirmacion_pdf").glob("*.py"):
        arbol = ast.parse(ruta_modulo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ImportFrom) or not nodo.module:
                continue
            if nodo.module == "app.application.use_cases.solicitudes.pdf_destino_policy":
                raise AssertionError(f"{ruta_modulo} importa pdf_destino_policy legacy")
            if nodo.module != "app.application.use_cases.solicitudes.auxiliares_caso_uso":
                continue
            nombres = {alias.name for alias in nodo.names}
            prohibidos = HELPERS_DESTINO_PROHIBIDOS.intersection(nombres)
            assert not prohibidos, (
                f"{ruta_modulo} importa helpers legacy de destino/preflight: {sorted(prohibidos)}"
            )
