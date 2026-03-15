from __future__ import annotations

from pathlib import Path


RUTA_SOLICITUDES = Path("app/application/use_cases/solicitudes")
ARCHIVOS_PERMITIDOS = {
    "confirmacion_pdf_service.py",
    "pdf_confirmadas_builder.py",
    "pdf_confirmadas_runner.py",
    "orquestacion_confirmacion.py",
}


def test_solicitudes_no_define_nuevos_modulos_pdf_confirmadas() -> None:
    archivos_pdf = {
        ruta.name
        for ruta in RUTA_SOLICITUDES.glob("*pdf*confirmad*.py")
    }
    assert archivos_pdf <= ARCHIVOS_PERMITIDOS
