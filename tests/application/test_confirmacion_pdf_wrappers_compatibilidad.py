from __future__ import annotations

from app.application.use_cases.confirmacion_pdf.path_file_system import PathFileSystem as PathFileSystemContexto
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder import (
    plan_pdf_confirmadas as plan_pdf_confirmadas_contexto,
)
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_runner import (
    run_pdf_confirmadas_plan as run_pdf_confirmadas_plan_contexto,
)
from app.application.use_cases.solicitudes.confirmacion_pdf_service import (
    PathFileSystem as PathFileSystemWrapper,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import (
    plan_pdf_confirmadas as plan_pdf_confirmadas_wrapper,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import (
    run_pdf_confirmadas_plan as run_pdf_confirmadas_plan_wrapper,
)


def test_wrapper_builder_reexporta_funcion_contexto() -> None:
    assert plan_pdf_confirmadas_wrapper is plan_pdf_confirmadas_contexto


def test_wrapper_runner_reexporta_funcion_contexto() -> None:
    assert run_pdf_confirmadas_plan_wrapper is run_pdf_confirmadas_plan_contexto


def test_wrapper_filesystem_reexporta_clase_contexto() -> None:
    assert PathFileSystemWrapper is PathFileSystemContexto
