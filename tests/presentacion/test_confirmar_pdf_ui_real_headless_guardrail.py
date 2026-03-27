from __future__ import annotations

import ast
from pathlib import Path


RUTA_TEST_UI_REAL = Path("tests/presentacion/test_confirmar_pdf_ui_real_contract.py")


def _llamadas_importorskip_pyqt(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if not isinstance(nodo.func, ast.Attribute):
            continue
        if nodo.func.attr != "importorskip":
            continue
        if not nodo.args or not isinstance(nodo.args[0], ast.Constant):
            continue
        valor = nodo.args[0].value
        if isinstance(valor, str) and valor.startswith("PySide6"):
            modulos.append(valor)
    return modulos


def test_confirmar_pdf_ui_real_prepara_headless_antes_de_importar_qt() -> None:
    contenido = RUTA_TEST_UI_REAL.read_text(encoding="utf-8")

    assert "preparar_entorno_qt_headless" in contenido
    assert "importar_qt_para_interfaz_real_o_omitir" in contenido
    assert _llamadas_importorskip_pyqt(RUTA_TEST_UI_REAL) == []
