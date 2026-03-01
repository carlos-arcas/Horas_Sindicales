from __future__ import annotations

import ast
from pathlib import Path

BUILDERS_DIR = Path("app/ui/vistas/builders")
EXTRA_CONTRACT_FILES = (
    Path("app/ui/vistas/main_window/wiring.py"),
    Path("app/ui/vistas/main_window/layout_builder.py"),
)
STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")


def _is_window_private_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "window"
        and isinstance(node.ctx, ast.Load)
        and node.attr.startswith("_")
    )


def _extract_window_handler_references(source: str, filename: str) -> set[str]:
    tree = ast.parse(source, filename=filename)
    return {
        node.attr
        for node in ast.walk(tree)
        if _is_window_private_attr(node)
    }


def _extract_main_window_private_methods(source: str, filename: str) -> set[str]:
    tree = ast.parse(source, filename=filename)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            return {
                method.name
                for method in node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                and method.name.startswith("_")
            }
    raise AssertionError(f"No se encontró class MainWindow en {filename}")


def _contract_files() -> tuple[Path, ...]:
    return tuple(sorted(BUILDERS_DIR.glob("*.py"))) + EXTRA_CONTRACT_FILES


def test_handlers_referenciados_en_builders_y_wiring_existen_en_main_window() -> None:
    usados: set[str] = set()

    for path in _contract_files():
        usados.update(
            _extract_window_handler_references(
                source=path.read_text(encoding="utf-8"),
                filename=str(path),
            )
        )

    definidos = _extract_main_window_private_methods(
        source=STATE_CONTROLLER.read_text(encoding="utf-8"),
        filename=str(STATE_CONTROLLER),
    )

    missing = sorted(usados - definidos)

    assert not missing, (
        "Faltan handlers requeridos por builders/wiring: "
        + ", ".join(missing)
    )
