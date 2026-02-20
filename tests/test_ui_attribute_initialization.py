from __future__ import annotations

import ast
from pathlib import Path


MAIN_WINDOW_FILE = Path(__file__).resolve().parents[1] / "app/ui/vistas/main_window_vista.py"
INIT_METHODS = {"__init__", "_create_widgets", "_build_ui"}


class MainWindowSelfAttributeAnalyzer(ast.NodeVisitor):
    """Analiza accesos/assigns de self.<attr> en MainWindow usando AST.

    Recorremos cada método de la clase y:
    - registramos los atributos self.<attr> usados (carga de valor),
    - registramos los atributos self.<attr> inicializados en los métodos permitidos.

    Se ignoran llamadas directas self.metodo() y referencias a métodos definidos en la
    propia clase (p. ej. señales: clicked.connect(self._on_sync)).
    """

    def __init__(self) -> None:
        self.used_attrs: set[str] = set()
        self.assigned_attrs: set[str] = set()
        self.class_method_names: set[str] = set()
        self._current_method: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name != "MainWindow":
            return

        self.class_method_names = {
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._current_method = item.name
                self.visit(item)
                self._current_method = None

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == "self" and isinstance(node.ctx, ast.Load):
            self.used_attrs.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
            # Ignoramos invocaciones directas self.metodo().
            for arg in node.args:
                self.visit(arg)
            for keyword in node.keywords:
                self.visit(keyword)
            return
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_method in INIT_METHODS:
            for target in node.targets:
                self._register_assignment_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._current_method in INIT_METHODS:
            self._register_assignment_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if self._current_method in INIT_METHODS:
            self._register_assignment_target(node.target)
        self.generic_visit(node)

    def _register_assignment_target(self, target: ast.expr) -> None:
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            self.assigned_attrs.add(target.attr)


def test_main_window_self_attributes_are_initialized() -> None:
    source = MAIN_WINDOW_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    analyzer = MainWindowSelfAttributeAnalyzer()
    analyzer.visit(tree)

    # Ignora referencias a métodos propios y posibles miembros privados heredados de Qt
    # (no definidos en MainWindow y normalmente con prefijo "_").
    private_inherited_qt = {
        attr
        for attr in analyzer.used_attrs
        if attr.startswith("_") and attr not in analyzer.class_method_names and attr not in analyzer.assigned_attrs
    }

    missing = sorted(
        attr
        for attr in analyzer.used_attrs
        if attr not in analyzer.assigned_attrs
        and attr not in analyzer.class_method_names
        and attr not in private_inherited_qt
    )

    assert not missing, (
        "MainWindow usa atributos self.* sin inicializar en __init__/_create_widgets/_build_ui: "
        f"{', '.join(missing)}"
    )
