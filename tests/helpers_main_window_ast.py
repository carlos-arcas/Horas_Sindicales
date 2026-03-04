from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUTAS_MAIN_WINDOW = (
    ROOT / "app/ui/vistas/main_window/state_controller.py",
    ROOT / "app/ui/vistas/main_window_vista.py",
    ROOT / "app/ui/main_window.py",
)
RUTA_MIXINS = ROOT / "app/ui/vistas/main_window"
RUTA_MIXIN_HEALTH = ROOT / "app/ui/vistas/main_window_health_mixin.py"


@dataclass(frozen=True)
class MetodoEncontrado:
    nombre: str
    nodo: ast.FunctionDef
    archivo: Path
    clase: str



def parsear_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))



def _iter_class_defs(path: Path) -> list[ast.ClassDef]:
    tree = parsear_ast(path)
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]



def _colectar_metodos(path: Path, class_name: str) -> dict[str, MetodoEncontrado]:
    methods: dict[str, MetodoEncontrado] = {}
    for class_node in _iter_class_defs(path):
        if class_node.name != class_name:
            continue
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods[node.name] = MetodoEncontrado(node.name, node, path, class_name)
    return methods



def metodos_main_window_directos() -> dict[str, MetodoEncontrado]:
    methods: dict[str, MetodoEncontrado] = {}
    for path in RUTAS_MAIN_WINDOW:
        if not path.exists():
            continue
        methods.update(_colectar_metodos(path, "MainWindow"))
    return methods



def metodos_main_window_mixins() -> dict[str, MetodoEncontrado]:
    methods: dict[str, MetodoEncontrado] = {}
    if RUTA_MIXINS.exists():
        for path in sorted(RUTA_MIXINS.glob("*.py")):
            for class_node in _iter_class_defs(path):
                if class_node.name == "MainWindow":
                    continue
                for node in class_node.body:
                    if isinstance(node, ast.FunctionDef):
                        methods[node.name] = MetodoEncontrado(node.name, node, path, class_node.name)
    if RUTA_MIXIN_HEALTH.exists():
        for class_node in _iter_class_defs(RUTA_MIXIN_HEALTH):
            if not class_node.name.endswith("Mixin"):
                continue
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    methods[node.name] = MetodoEncontrado(
                        node.name,
                        node,
                        RUTA_MIXIN_HEALTH,
                        class_node.name,
                    )
    return methods



def resolver_metodo_main_window(method_name: str) -> MetodoEncontrado | None:
    directos = metodos_main_window_directos()
    if method_name in directos:
        return directos[method_name]
    return metodos_main_window_mixins().get(method_name)



def resolver_metodo_wrapper(method_name: str) -> MetodoEncontrado | None:
    directos = metodos_main_window_directos()
    found = directos.get(method_name)
    if found is None:
        return None
    if found.archivo in {
        ROOT / "app/ui/vistas/main_window/state_controller.py",
        ROOT / "app/ui/vistas/main_window_vista.py",
    }:
        return found
    return None



def metodo_existe_en_mainwindow_o_mixins(method_name: str) -> bool:
    return resolver_metodo_main_window(method_name) is not None



def firma_acepta_argumento_senal(method: ast.FunctionDef) -> bool:
    posicionables = len(method.args.posonlyargs) + len(method.args.args)
    return method.args.vararg is not None or posicionables >= 2



def es_wrapper_super_minimo(method: ast.FunctionDef, method_name: str) -> bool:
    if len(method.body) != 1:
        return False
    stmt = method.body[0]
    if isinstance(stmt, ast.Return):
        call = stmt.value
    elif isinstance(stmt, ast.Expr):
        call = stmt.value
    else:
        return False
    if not isinstance(call, ast.Call):
        return False
    if not isinstance(call.func, ast.Attribute):
        return False
    if call.func.attr != method_name:
        return False
    if not isinstance(call.func.value, ast.Call):
        return False
    super_call = call.func.value
    return isinstance(super_call.func, ast.Name) and super_call.func.id == "super"
