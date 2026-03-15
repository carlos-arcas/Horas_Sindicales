from __future__ import annotations

import ast
from pathlib import Path


RUTA_SOLICITUDES_USE_CASE = Path("app/application/use_cases/solicitudes/use_case.py")
RUTA_CONTROLLER_SOLICITUDES = Path("app/ui/controllers/solicitudes_controller.py")
RUTA_ADAPTADOR_CONFIRMACION_QT = Path("app/ui/vistas/confirmacion_adaptador_qt.py")
RUTA_HISTORICO_ACTIONS = Path("app/ui/vistas/historico_actions.py")
RUTA_ACCIONES_MIXIN = Path("app/ui/vistas/main_window/acciones_mixin.py")


def _metodos_publicos(path_archivo: Path, *, clase: str) -> set[str]:
    arbol = ast.parse(path_archivo.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef) and nodo.name == clase:
            return {
                funcion.name
                for funcion in nodo.body
                if isinstance(funcion, ast.FunctionDef)
                and not funcion.name.startswith("_")
            }
    raise AssertionError(f"No se encontró la clase {clase} en {path_archivo}")


def test_solicitud_use_cases_reduce_wrappers_confirmacion_pdf_legacy() -> None:
    metodos_publicos = _metodos_publicos(
        RUTA_SOLICITUDES_USE_CASE,
        clase="SolicitudUseCases",
    )

    assert "sugerir_nombre_pdf" not in metodos_publicos
    assert "resolver_destino_pdf" not in metodos_publicos
    assert "confirmar_y_generar_pdf_por_filtro" not in metodos_publicos

    assert "confirmar_lote_y_generar_pdf" in metodos_publicos
    assert "confirmar_y_generar_pdf" in metodos_publicos
    assert "coordinador_confirmacion_pdf" in metodos_publicos


def test_consumidores_ui_confirmacion_pdf_evitan_service_locator_solicitud_use_cases() -> None:
    rutas = [
        RUTA_CONTROLLER_SOLICITUDES,
        RUTA_ADAPTADOR_CONFIRMACION_QT,
        RUTA_HISTORICO_ACTIONS,
        RUTA_ACCIONES_MIXIN,
    ]
    contenido = "\n".join(ruta.read_text(encoding="utf-8") for ruta in rutas)

    assert "_solicitud_use_cases.coordinador_confirmacion_pdf" not in contenido
    assert "_coordinador_confirmacion_pdf" in contenido
    assert "_solicitud_use_cases.sugerir_nombre_pdf(" not in contenido
    assert "_solicitud_use_cases.resolver_destino_pdf(" not in contenido
    assert "_solicitud_use_cases.confirmar_y_generar_pdf_por_filtro(" not in contenido
