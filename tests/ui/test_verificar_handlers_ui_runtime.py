from __future__ import annotations

import ast
from pathlib import Path

RUTA_ACCIONES_MIXIN = Path("app/ui/vistas/main_window/acciones_mixin.py")
RUTA_INICIALIZACION = Path("app/ui/vistas/main_window/inicializacion_mixin.py")


class _LoggerFalso:
    def error(self, *_args, **_kwargs) -> None:
        return None


def _resolver_clase(tree: ast.Module, nombre: str) -> ast.ClassDef:
    return next(
        nodo for nodo in tree.body if isinstance(nodo, ast.ClassDef) and nodo.name == nombre
    )


def _cargar_verificador_y_handlers() -> tuple[tuple[str, ...], object]:
    tree = ast.parse(RUTA_ACCIONES_MIXIN.read_text(encoding="utf-8"), filename=str(RUTA_ACCIONES_MIXIN))
    asignacion = next(
        nodo
        for nodo in tree.body
        if isinstance(nodo, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "HANDLERS_UI_CRITICOS" for target in nodo.targets)
    )
    clase = _resolver_clase(tree, "AccionesMainWindowMixin")
    metodo = next(
        nodo for nodo in clase.body if isinstance(nodo, ast.FunctionDef) and nodo.name == "_verificar_handlers_ui"
    )
    modulo = ast.Module(body=[asignacion, metodo], type_ignores=[])
    ast.fix_missing_locations(modulo)
    namespace: dict[str, object] = {"logger": _LoggerFalso()}
    exec(compile(modulo, str(RUTA_ACCIONES_MIXIN), "exec"), namespace)
    return namespace["HANDLERS_UI_CRITICOS"], namespace["_verificar_handlers_ui"]


def test_verificar_handlers_ui_valida_handlers_criticos() -> None:
    handlers, verificador = _cargar_verificador_y_handlers()

    class VentanaValida:
        pass

    for nombre in handlers:
        setattr(VentanaValida, nombre, lambda self, *args, **kwargs: None)

    verificador(VentanaValida())


def test_verificar_handlers_ui_falla_con_mensaje_claro_si_falta_handler() -> None:
    handlers, verificador = _cargar_verificador_y_handlers()

    class VentanaInvalida:
        pass

    for nombre in handlers:
        setattr(VentanaInvalida, nombre, lambda self, *args, **kwargs: None)
    ventana = VentanaInvalida()
    ventana._on_open_saldos_modal = None

    try:
        verificador(ventana)
    except RuntimeError as exc:
        mensaje = str(exc)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba RuntimeError por handler faltante")

    assert "Contrato UI MainWindow inválido" in mensaje
    assert "_on_open_saldos_modal" in mensaje


def test_build_ui_ejecuta_verificacion_antes_de_wiring() -> None:
    tree = ast.parse(RUTA_INICIALIZACION.read_text(encoding="utf-8"), filename=str(RUTA_INICIALIZACION))
    clase = _resolver_clase(tree, "InicializacionMainWindowMixin")
    metodo = next(
        nodo for nodo in clase.body if isinstance(nodo, ast.FunctionDef) and nodo.name == "_build_ui"
    )

    primera_sentencia = metodo.body[0]
    assert isinstance(primera_sentencia, ast.Expr)
    llamada = primera_sentencia.value
    assert isinstance(llamada, ast.Call)
    assert ast.unparse(llamada.func) == "self._verificar_handlers_ui"
    assert ast.unparse(llamada) == "self._verificar_handlers_ui()"
