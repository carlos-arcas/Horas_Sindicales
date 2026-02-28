from __future__ import annotations

import ast
from pathlib import Path

RUTA_STATE = Path("app/ui/vistas/main_window/state_controller.py")
RUTA_DIALOGOS = Path("app/ui/vistas/main_window/layout_builder.py")
CLASES = {"OptionalConfirmDialog", "PdfPreviewDialog", "HistoricoDetalleDialog"}


def _class_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def test_state_controller_ya_no_declara_dialogos_extraidos() -> None:
    class_names = _class_names(RUTA_STATE)
    assert CLASES.isdisjoint(class_names)


def test_layout_builder_declara_clases_extraidas() -> None:
    class_names = _class_names(RUTA_DIALOGOS)
    assert CLASES.issubset(class_names)
