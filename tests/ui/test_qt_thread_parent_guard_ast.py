from __future__ import annotations

import ast

import pytest
from pathlib import Path

pytestmark = pytest.mark.headless_safe

ROOT_APP = Path("app")

MENSAJE_ERROR = (
    "Uso prohibido de QApplication.instance()/qApp como parent de QObject. "
    "Inyecta parent explícito del hilo correcto o usa None en servicios no-UI."
)

EXCEPCIONES_UI_HILO_PRINCIPAL: dict[str, str] = {}

CLASES_QOBJECT_COMUNES = {"QObject", "QSettings", "QTimer"}


class _GuardVisitor(ast.NodeVisitor):
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.violaciones: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if self._parent_keyword_es_qapp_instance(node):
            self._agregar_violacion(node, "keyword parent=QApplication.instance()/qApp")
        if self._first_arg_es_qapp_instance_en_qobject(node):
            self._agregar_violacion(node, "primer argumento parent=QApplication.instance()")
        self.generic_visit(node)

    def _agregar_violacion(self, node: ast.AST, regla: str) -> None:
        self.violaciones.append(f"{self.source_path}:{node.lineno} -> {regla}")

    @staticmethod
    def _es_qapplication_instance(node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        if not isinstance(node.func, ast.Attribute):
            return False
        return (
            node.func.attr == "instance"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "QApplication"
            and not node.args
            and not node.keywords
        )

    def _parent_keyword_es_qapp_instance(self, call: ast.Call) -> bool:
        for keyword in call.keywords:
            if keyword.arg != "parent":
                continue
            if isinstance(keyword.value, ast.Name) and keyword.value.id == "qApp":
                return True
            if self._es_qapplication_instance(keyword.value):
                return True
        return False

    def _first_arg_es_qapp_instance_en_qobject(self, call: ast.Call) -> bool:
        if not call.args or not self._es_qapplication_instance(call.args[0]):
            return False
        if isinstance(call.func, ast.Name):
            return call.func.id in CLASES_QOBJECT_COMUNES
        if isinstance(call.func, ast.Attribute):
            return call.func.attr in CLASES_QOBJECT_COMUNES
        return False


def _modulo_justificado(path: Path) -> bool:
    return path.as_posix() in EXCEPCIONES_UI_HILO_PRINCIPAL


def test_guard_parent_qapplication_instance_por_ast() -> None:
    violaciones: list[str] = []
    for source_path in sorted(ROOT_APP.rglob("*.py")):
        if _modulo_justificado(source_path):
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        visitor = _GuardVisitor(source_path)
        visitor.visit(tree)
        violaciones.extend(visitor.violaciones)

    assert not violaciones, f"{MENSAJE_ERROR}\n" + "\n".join(violaciones)
