from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers_main_window_ast import (
    es_wrapper_super_minimo,
    resolver_metodo_main_window,
    resolver_metodo_wrapper,
)


RUTA_INICIALIZACION_MIXIN = Path(
    "app/ui/vistas/main_window/inicializacion_mixin.py"
)
RUTA_REFRESCO_MIXIN = Path("app/ui/vistas/main_window/refresco_mixin.py")


def _get_method_node(method_name: str) -> ast.FunctionDef:
    encontrado = resolver_metodo_main_window(method_name)
    assert encontrado is not None, f"No se encontró {method_name} en MainWindow/mixins"
    return encontrado.nodo


def _get_class_method(path: Path, class_name: str, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return child
    raise AssertionError(f"No se encontró {class_name}.{method_name} en {path}")


def _assigns_attr(method: ast.FunctionDef, attr_name: str) -> bool:
    return any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == attr_name
            for target in node.targets
        )
        for node in method.body
    )


def _calls_attr(method: ast.FunctionDef, attr_name: str) -> int:
    return sum(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr_name
        for node in ast.walk(method)
    )


def test_on_fecha_changed_tiene_firma_qdate() -> None:
    method = _get_method_node("_on_fecha_changed")
    assert len(method.args.args) == 2
    arg = method.args.args[1]
    assert arg.arg == "qdate"
    assert isinstance(arg.annotation, ast.Name)
    assert arg.annotation.id == "QDate"


def test_wrapper_on_fecha_changed_delega_solo_en_super() -> None:
    wrapper = resolver_metodo_wrapper("_on_fecha_changed")
    assert wrapper is not None
    assert es_wrapper_super_minimo(wrapper.nodo, "_on_fecha_changed")


def test_wrapper_on_fecha_changed_no_duplica_estado_ni_preview() -> None:
    wrapper = resolver_metodo_wrapper("_on_fecha_changed")
    assert wrapper is not None
    assert not _assigns_attr(wrapper.nodo, "_fecha_seleccionada")
    assert _calls_attr(wrapper.nodo, "_update_solicitud_preview") == 0


def test_fuente_de_verdad_base_actualiza_estado_y_refresca_operativa() -> None:
    base = _get_class_method(
        RUTA_INICIALIZACION_MIXIN,
        "InicializacionMainWindowMixin",
        "_on_fecha_changed",
    )

    assert _assigns_attr(base, "_fecha_seleccionada")
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "_refrescar_estado_operativa"
        for node in ast.walk(base)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "refrescar_operativa"
        for node in ast.walk(base)
    )
    assert _calls_attr(base, "_update_solicitud_preview") == 0


def test_refresco_operativa_actualiza_preview_una_sola_vez() -> None:
    refresh = _get_class_method(
        RUTA_REFRESCO_MIXIN,
        "RefrescoMainWindowMixin",
        "_refrescar_estado_operativa",
    )

    assert _calls_attr(refresh, "_update_solicitud_preview") == 1


def test_guardrail_no_reaparece_patron_actualizar_local_y_delegar_a_super() -> None:
    wrapper = resolver_metodo_wrapper("_on_fecha_changed")
    assert wrapper is not None

    assert not _assigns_attr(wrapper.nodo, "_fecha_seleccionada")
    assert _calls_attr(wrapper.nodo, "_update_solicitud_preview") == 0
    assert es_wrapper_super_minimo(wrapper.nodo, "_on_fecha_changed")
