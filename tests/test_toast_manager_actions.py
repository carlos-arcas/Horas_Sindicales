from __future__ import annotations

import ast
import logging
from pathlib import Path

from app.ui.toasts.ejecutar_callback_seguro import ejecutar_callback_seguro


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module_ast(relative_path: str) -> ast.Module:
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return ast.parse(source)


def _get_class_method(module: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"No se encontró {class_name}.{method_name}")


def test_success_and_error_signature_support_action_params() -> None:
    module = _load_module_ast("app/ui/widgets/toast.py")

    for method_name in ("success", "error"):
        method = _get_class_method(module, "GestorToasts", method_name)
        kwonly = {arg.arg for arg in method.args.kwonlyargs}
        assert "action_label" in kwonly
        assert "action_callback" in kwonly


def test_payload_internal_contains_action_fields() -> None:
    module = _load_module_ast("app/ui/widgets/gestor_toasts.py")
    method = _get_class_method(module, "GestorToasts", "_crear_notificacion")

    notificacion_calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "NotificacionToast"
    ]
    assert notificacion_calls, "No se encontró construcción de NotificacionToast"

    keywords = {kw.arg for kw in notificacion_calls[0].keywords}
    assert "action_label" in keywords
    assert "action_callback" in keywords


def test_safe_wrapper_swallows_callback_exception_and_logs(caplog) -> None:
    caplog.set_level(logging.ERROR)

    def _boom() -> None:
        raise RuntimeError("boom")

    result = ejecutar_callback_seguro(
        _boom,
        logger=logging.getLogger("tests.toast"),
        contexto="toast:error:Reintentar",
        correlation_id="abc-123",
    )

    assert result is False
    assert "TOAST_ACTION_FAILED" in caplog.text
