from __future__ import annotations

import ast
from pathlib import Path


RAIZ_REPO = Path(__file__).resolve().parents[1]
RUTA_ESTADO_MIXIN = RAIZ_REPO / "app/ui/vistas/main_window/estado_mixin.py"
RUTA_STATE_CONTROLLER = RAIZ_REPO / "app/ui/vistas/main_window/state_controller.py"


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_estado_mixin_propaga_select_id_a_fuente_real() -> None:
    modulo = _parse_file(RUTA_ESTADO_MIXIN)
    metodo = next(
        nodo
        for nodo in ast.walk(modulo)
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "_load_personas"
    )

    argumentos = [argumento.arg for argumento in metodo.args.args]
    assert argumentos == ["self", "select_id"]

    retorno = next(
        nodo for nodo in metodo.body if isinstance(nodo, ast.Return)
    )
    llamada = retorno.value
    assert isinstance(llamada, ast.Call)
    assert isinstance(llamada.func, ast.Attribute)
    assert llamada.func.attr == "load_personas"
    assert len(llamada.keywords) == 1
    keyword = llamada.keywords[0]
    assert keyword.arg == "select_id"
    assert isinstance(keyword.value, ast.Name)
    assert keyword.value.id == "select_id"


def test_mainwindow_no_reintroduce_fallback_fantasma_en_load_personas() -> None:
    contenido = RUTA_STATE_CONTROLLER.read_text(encoding="utf-8")

    assert "def _load_personas(" not in contenido
    assert "_seleccionar_persona_por_id" not in contenido
    assert "_set_persona_activa_por_id" not in contenido
    assert "_aplicar_persona_seleccionada" not in contenido
