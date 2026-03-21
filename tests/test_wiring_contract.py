from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from tests.helpers_main_window_ast import (
    metodos_main_window_directos,
    metodos_main_window_mixins,
)

_RUTAS_WIRING = (
    Path("app/ui/vistas/builders"),
    Path("app/ui/vistas/main_window"),
)
_ARCHIVO_BINDINGS = Path("app/ui/vistas/main_window/state_bindings.py")
_ARCHIVO_HISTORICO_ACTIONS = Path("app/ui/vistas/historico_actions.py")
_ARCHIVO_STATE_HISTORICO = Path("app/ui/vistas/main_window/state_historico.py")
_SENALES_QT_CON_ARG = {"dateChanged", "timeChanged", "toggled"}


@dataclass(frozen=True)
class ReferenciaHandler:
    handler: str
    signal_name: str | None
    archivo: Path
    linea: int


@dataclass(frozen=True)
class FirmaFuncion:
    posicionables: int
    acepta_varargs: bool

    def acepta_argumento_senal(self) -> bool:
        return self.acepta_varargs or self.posicionables >= 2


class _ExtractorReferencias(ast.NodeVisitor):
    def __init__(self, archivo: Path) -> None:
        self._archivo = archivo
        self.referencias: list[ReferenciaHandler] = []

    def visit_Call(self, node: ast.Call) -> None:
        referencia_connect = self._parse_connect(node)
        if referencia_connect is not None:
            self.referencias.append(referencia_connect)
        referencia_helper = self._parse_conectar_signal(node)
        if referencia_helper is not None:
            self.referencias.append(referencia_helper)
        self.generic_visit(node)

    def _parse_connect(self, node: ast.Call) -> ReferenciaHandler | None:
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "connect"):
            return None
        if not node.args:
            return None
        handler = self._handler_desde_attr_window(node.args[0])
        signal_name = self._signal_name(node.func.value)
        if handler is None:
            return None
        return ReferenciaHandler(handler, signal_name, self._archivo, node.lineno)

    def _parse_conectar_signal(self, node: ast.Call) -> ReferenciaHandler | None:
        if not (isinstance(node.func, ast.Name) and node.func.id == "conectar_signal"):
            return None
        signal_name = self._signal_name(node.args[1]) if len(node.args) > 1 else None
        handler = self._handler_name_conectar_signal(node)
        if handler is None:
            return None
        return ReferenciaHandler(handler, signal_name, self._archivo, node.lineno)

    def _handler_name_conectar_signal(self, node: ast.Call) -> str | None:
        if (
            len(node.args) > 2
            and isinstance(node.args[2], ast.Constant)
            and isinstance(node.args[2].value, str)
        ):
            return node.args[2].value
        for keyword in node.keywords:
            if keyword.arg == "handler_name" and isinstance(
                keyword.value, ast.Constant
            ):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value
        if (
            len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            return node.args[1].value
        return None

    def _signal_name(self, expr: ast.expr) -> str | None:
        if isinstance(expr, ast.Attribute):
            return expr.attr
        return None

    def _handler_desde_attr_window(self, expr: ast.expr) -> str | None:
        if not isinstance(expr, ast.Attribute):
            return None
        if isinstance(expr.value, ast.Name) and expr.value.id == "window":
            return expr.attr
        return None


def _iter_archivos_wiring() -> list[Path]:
    archivos: list[Path] = []
    for ruta in _RUTAS_WIRING:
        archivos.extend(sorted(ruta.rglob("*.py")))
    return archivos


def _parse_file(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _extraer_referencias_handlers() -> list[ReferenciaHandler]:
    referencias: list[ReferenciaHandler] = []
    for archivo in _iter_archivos_wiring():
        extractor = _ExtractorReferencias(archivo)
        extractor.visit(_parse_file(archivo))
        referencias.extend(extractor.referencias)
    return referencias


def _firma_from_args(args: ast.arguments) -> FirmaFuncion:
    posicionables = len(args.posonlyargs) + len(args.args)
    acepta_varargs = args.vararg is not None
    return FirmaFuncion(posicionables=posicionables, acepta_varargs=acepta_varargs)


def _collect_handlers_main_window() -> dict[str, FirmaFuncion]:
    handlers: dict[str, FirmaFuncion] = {}
    for encontrado in metodos_main_window_mixins().values():
        handlers[encontrado.nombre] = _firma_from_args(encontrado.nodo.args)
    for encontrado in metodos_main_window_directos().values():
        handlers[encontrado.nombre] = _firma_from_args(encontrado.nodo.args)
    return handlers


def _collect_binding_handlers() -> dict[str, tuple[Path, str]]:
    tree = _parse_file(_ARCHIVO_BINDINGS)
    bindings: dict[str, tuple[Path, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=False):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                continue
            if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                if value.value.id == "historico_actions":
                    bindings[key.value] = (_ARCHIVO_HISTORICO_ACTIONS, value.attr)
                if value.value.id == "state_historico":
                    bindings[key.value] = (_ARCHIVO_STATE_HISTORICO, value.attr)
    return bindings


def _collect_signatures(path: Path) -> dict[str, FirmaFuncion]:
    tree = _parse_file(path)
    signatures: dict[str, FirmaFuncion] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            signatures[node.name] = _firma_from_args(node.args)
    return signatures


def test_contrato_wiring_handlers_existentes_en_main_window() -> None:
    handlers_main_window = _collect_handlers_main_window()
    bindings = _collect_binding_handlers()
    faltantes: list[str] = []

    for referencia in _extraer_referencias_handlers():
        if referencia.handler in handlers_main_window or referencia.handler in bindings:
            continue
        faltantes.append(
            f"{referencia.archivo}:{referencia.linea} -> {referencia.handler}"
        )

    assert not faltantes, "Handlers inexistentes en wiring:\n" + "\n".join(faltantes)


def test_firma_on_historico_periodo_mode_changed_acepta_argumento_extra() -> None:
    historico_signatures = _collect_signatures(_ARCHIVO_HISTORICO_ACTIONS)
    firma = historico_signatures["on_historico_periodo_mode_changed"]
    assert firma.acepta_argumento_senal()


def test_handlers_de_senales_qt_conocidas_aceptan_argumento() -> None:
    handlers_main_window = _collect_handlers_main_window()
    bindings = _collect_binding_handlers()
    signatures_por_archivo = {
        _ARCHIVO_HISTORICO_ACTIONS: _collect_signatures(_ARCHIVO_HISTORICO_ACTIONS),
        _ARCHIVO_STATE_HISTORICO: _collect_signatures(_ARCHIVO_STATE_HISTORICO),
    }
    invalidos: list[str] = []

    for referencia in _extraer_referencias_handlers():
        if referencia.signal_name not in _SENALES_QT_CON_ARG:
            continue
        firma = handlers_main_window.get(referencia.handler)
        if firma is None and referencia.handler in bindings:
            archivo_binding, nombre_funcion = bindings[referencia.handler]
            firma = signatures_por_archivo[archivo_binding].get(nombre_funcion)
        if firma is not None and firma.acepta_argumento_senal():
            continue
        invalidos.append(
            f"{referencia.archivo}:{referencia.linea} -> {referencia.handler}"
        )

    assert not invalidos, "Handlers con firma incompatible:\n" + "\n".join(invalidos)


def test_state_actions_apply_historico_filters_delega_a_historico_actions() -> None:
    tree = _parse_file(Path("app/ui/vistas/main_window/state_actions.py"))

    for node in tree.body:
        if (
            not isinstance(node, ast.ClassDef)
            or node.name != "MainWindowStateActionsMixin"
        ):
            continue
        for method in node.body:
            if (
                not isinstance(method, ast.FunctionDef)
                or method.name != "_apply_historico_filters"
            ):
                continue
            assert len(method.body) == 1
            sentencia = method.body[0]
            assert isinstance(sentencia, ast.Expr)
            llamada = sentencia.value
            assert isinstance(llamada, ast.Call)
            assert isinstance(llamada.func, ast.Attribute)
            assert isinstance(llamada.func.value, ast.Name)
            assert llamada.func.value.id == "historico_actions"
            assert llamada.func.attr == "apply_historico_filters"
            assert len(llamada.args) == 1
            assert isinstance(llamada.args[0], ast.Name)
            assert llamada.args[0].id == "self"
            return

    raise AssertionError(
        "No se encontró MainWindowStateActionsMixin._apply_historico_filters"
    )
