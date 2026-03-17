from __future__ import annotations

import ast
from pathlib import Path


RUTA_CASO_USO = Path("app/application/use_cases/confirmacion_pdf/generar_pdf_confirmadas_caso_uso.py")
RUTA_SOLICITUDES_USE_CASE = Path("app/application/use_cases/solicitudes/use_case.py")
RUTA_COORDINADOR = Path("app/application/use_cases/confirmacion_pdf/coordinador_confirmacion_pdf.py")
RUTA_SERVICIO_DESTINO = Path("app/application/use_cases/confirmacion_pdf/servicio_destino_pdf_confirmacion.py")


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


def test_solicitudes_use_case_no_concentra_orquestacion_confirmacion_pdf() -> None:
    imports = _imports_desde_modulo(RUTA_SOLICITUDES_USE_CASE)

    assert "app.application.use_cases.confirmacion_pdf.coordinador_confirmacion_pdf" in imports
    assert "app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf" not in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder" not in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner" not in imports
    assert "app.application.use_cases.solicitudes.confirmacion_pdf_service" not in imports


def test_coordinador_confirmacion_pdf_delega_destino_en_servicio_dedicado() -> None:
    imports = _imports_desde_modulo(RUTA_COORDINADOR)

    assert "app.application.use_cases.confirmacion_pdf.orquestacion_confirmacion_pdf" in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder" in imports
    assert "app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner" in imports
    assert "app.application.use_cases.confirmacion_pdf.servicio_destino_pdf_confirmacion" in imports
    assert "app.application.use_cases.solicitudes.pdf_destino_policy" not in imports


def test_servicio_destino_confirmacion_no_depende_de_helpers_solicitudes() -> None:
    imports = _imports_desde_modulo(RUTA_SERVICIO_DESTINO)

    assert "app.application.use_cases.solicitudes.auxiliares_caso_uso" not in imports
    assert "app.application.use_cases.solicitudes.pdf_destino_policy" not in imports
    assert "app.application.use_cases.confirmacion_pdf.destino_pdf_policy" in imports
