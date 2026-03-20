from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


RUTA_MAIN_WINDOW_VISTA = Path("app/ui/vistas/main_window_vista.py")
RUTA_STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
RUTA_MIXINS = {
    "AccionesMainWindowMixin": Path("app/ui/vistas/main_window/acciones_mixin.py"),
    "EstadoMainWindowMixin": Path("app/ui/vistas/main_window/estado_mixin.py"),
    "InicializacionMainWindowMixin": Path("app/ui/vistas/main_window/inicializacion_mixin.py"),
    "NavegacionMainWindowMixin": Path("app/ui/vistas/main_window/navegacion_mixin.py"),
    "RefrescoMainWindowMixin": Path("app/ui/vistas/main_window/refresco_mixin.py"),
    "MainWindowStateActionsMixin": Path("app/ui/vistas/main_window/state_actions.py"),
    "MainWindowStateValidationMixin": Path("app/ui/vistas/main_window/state_validations.py"),
    "MainWindowHealthMixin": Path("app/ui/vistas/main_window_health_mixin.py"),
}


@dataclass(frozen=True)
class MetodoClase:
    archivo: Path
    clase: str
    nodo: ast.FunctionDef


def _parsear(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _clase(tree: ast.Module, nombre: str) -> ast.ClassDef:
    return next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == nombre
    )


def _cuerpo_sin_docstring(method: ast.FunctionDef) -> list[ast.stmt]:
    body = list(method.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _es_super_wrapper_minimo(method: ast.FunctionDef) -> bool:
    body = _cuerpo_sin_docstring(method)
    if len(body) != 1:
        return False
    stmt = body[0]
    if not isinstance(stmt, ast.Return):
        return False
    call = stmt.value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
        return False
    super_call = call.func.value
    return (
        isinstance(super_call, ast.Call)
        and isinstance(super_call.func, ast.Name)
        and super_call.func.id == "super"
    )


def _extraer_super_wrapper_minimos(path: Path, class_name: str) -> dict[str, ast.FunctionDef]:
    class_node = _clase(_parsear(path), class_name)
    wrappers: dict[str, ast.FunctionDef] = {}
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and _es_super_wrapper_minimo(node):
            wrappers[node.name] = node
    return wrappers


def _metodos_clase(path: Path, class_name: str) -> dict[str, MetodoClase]:
    class_node = _clase(_parsear(path), class_name)
    return {
        node.name: MetodoClase(path, class_name, node)
        for node in class_node.body
        if isinstance(node, ast.FunctionDef)
    }


def _orden_busqueda_super() -> list[tuple[str, dict[str, MetodoClase]]]:
    state_methods = _metodos_clase(RUTA_STATE_CONTROLLER, "MainWindow")
    order: list[tuple[str, dict[str, MetodoClase]]] = [("MainWindow", state_methods)]
    state_class = _clase(_parsear(RUTA_STATE_CONTROLLER), "MainWindow")
    bases = [ast.unparse(base) for base in state_class.bases if ast.unparse(base) != "QMainWindow"]
    for base_name in bases:
        path = RUTA_MIXINS.get(base_name)
        if path is None:
            continue
        order.append((base_name, _metodos_clase(path, base_name)))
    return order


def _target_super_efectivo(method_name: str) -> MetodoClase | None:
    for _, methods in _orden_busqueda_super():
        target = methods.get(method_name)
        if target is not None:
            return target
    return None


def _argumentos_requeridos(method: ast.FunctionDef) -> tuple[int, bool]:
    posicionales = list(method.args.posonlyargs) + list(method.args.args)
    if posicionales and posicionales[0].arg == "self":
        posicionales = posicionales[1:]
    requeridos = len(posicionales) - len(method.args.defaults)
    return requeridos, method.args.vararg is not None


def _cantidad_argumentos_wrapper(method: ast.FunctionDef) -> int:
    body = _cuerpo_sin_docstring(method)
    call = body[0].value
    assert isinstance(call, ast.Call)
    return len(call.args) + len(call.keywords)


def test_main_window_vista_super_wrappers_apuntan_a_metodos_reales() -> None:
    wrappers = _extraer_super_wrapper_minimos(RUTA_MAIN_WINDOW_VISTA, "MainWindow")
    rotos: list[str] = []

    for name, wrapper in sorted(wrappers.items()):
        target = _target_super_efectivo(name)
        if target is None:
            rotos.append(
                f"{name}: super() no resuelve ningún método en la jerarquía efectiva de MainWindow"
            )
            continue
        requeridos, acepta_varargs = _argumentos_requeridos(target.nodo)
        enviados = _cantidad_argumentos_wrapper(wrapper)
        if enviados < requeridos or (enviados > requeridos and not acepta_varargs):
            rotos.append(
                f"{name}: wrapper envía {enviados} args pero {target.clase}.{name} en "
                f"{target.archivo} exige {requeridos}{'+' if acepta_varargs else ''}"
            )

    assert not rotos, (
        "Se detectaron wrappers super() rotos en app/ui/vistas/main_window_vista.py:\n- "
        + "\n- ".join(rotos)
    )


def test_main_window_vista_guardrail_incluye_wrappers_clave() -> None:
    wrappers = _extraer_super_wrapper_minimos(RUTA_MAIN_WINDOW_VISTA, "MainWindow")
    expected = {
        "_apply_sync_report",
        "_clear_form",
        "_confirmar_cambio_delegada",
        "_limpiar_formulario",
        "_save_current_draft",
        "_show_error_detail",
        "_sync_historico_select_all_visible_state",
        "_verificar_handlers_ui",
    }
    faltantes = sorted(expected - set(wrappers))
    assert not faltantes, (
        "El guardrail perdió wrappers mínimos relevantes de main_window_vista.py: "
        + ", ".join(faltantes)
    )
