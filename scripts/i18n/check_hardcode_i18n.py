from __future__ import annotations

import ast
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

METODOS_LOGGER = {"debug", "info", "warning", "error", "exception", "critical", "log"}
PATRON_CLAVE_I18N = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"
PATRONES_TECNICOS_DEFAULT = (r"^%[YmdHMS:\-_/ ]+$", r"^(utf-8|ascii|latin-1)$")


@dataclass(frozen=True)
class Hallazgo:
    ruta_relativa: str
    lineno: int
    texto: str
    regla: str = "I18N_HARDCODE"


@dataclass(frozen=True)
class ConfigCheck:
    rutas_objetivo: tuple[str, ...] = ("presentacion", "app/ui")
    rutas_excluidas: tuple[str, ...] = ("tests", "docs", "migrations", "__pycache__")
    archivos_excluidos: tuple[str, ...] = (
        "presentacion/i18n/**",
        "app/ui/i18n/**",
        "infraestructura/i18n/**",
        "app/ui/copy_catalog.py",
    )
    patron_clave_i18n: str = PATRON_CLAVE_I18N
    patrones_tecnicos_permitidos: tuple[str, ...] = PATRONES_TECNICOS_DEFAULT
    wrappers_logger_permitidos: tuple[str, ...] = ()
    recorte_texto: int = 80
    extensiones: tuple[str, ...] = (".py",)
    metodos_logger: tuple[str, ...] = field(default_factory=lambda: tuple(METODOS_LOGGER))


class _VisitanteHardcode(ast.NodeVisitor):
    def __init__(self, ruta_relativa: str, config: ConfigCheck) -> None:
        self._ruta_relativa = ruta_relativa
        self._config = config
        self._hallazgos: list[Hallazgo] = []
        self._padres: dict[ast.AST, ast.AST] = {}

    def analizar(self, modulo: ast.AST) -> list[Hallazgo]:
        self._indexar_padres(modulo)
        self.visit(modulo)
        return self._hallazgos

    def _indexar_padres(self, modulo: ast.AST) -> None:
        for parent in ast.walk(modulo):
            for child in ast.iter_child_nodes(parent):
                self._padres[child] = parent

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        if isinstance(node.value, str):
            self._analizar_texto(node, node.value)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802
        partes = [item.value for item in node.values if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        if partes:
            self._analizar_texto(node, "".join(partes))
        self.generic_visit(node)

    def _analizar_texto(self, node: ast.AST, texto: str) -> None:
        if not self._es_hardcode_visible(node, texto):
            return
        self._hallazgos.append(
            Hallazgo(
                ruta_relativa=self._ruta_relativa,
                lineno=getattr(node, "lineno", 1),
                texto=_recortar_texto(texto, self._config.recorte_texto),
            )
        )

    def _es_hardcode_visible(self, node: ast.AST, texto: str) -> bool:
        if not texto.strip() or _es_docstring(node, self._padres):
            return False
        if re.fullmatch(self._config.patron_clave_i18n, texto):
            return False
        if _coincide_alguno(texto, self._config.patrones_tecnicos_permitidos):
            return False
        return not _en_contexto_logger(node, self._padres, self._config)


def analizar_ruta(ruta_base: Path, config: ConfigCheck) -> list[Hallazgo]:
    if not ruta_base.exists():
        return []

    raiz_repo = _resolver_raiz_repo(ruta_base)
    if ruta_base.is_file():
        return _analizar_archivo(ruta_base, raiz_repo, config)

    hallazgos: list[Hallazgo] = []
    for archivo in sorted(ruta_base.rglob("*")):
        if not archivo.is_file() or archivo.suffix not in config.extensiones:
            continue
        hallazgos.extend(_analizar_archivo(archivo, raiz_repo, config))
    return sorted(hallazgos, key=lambda item: (item.ruta_relativa, item.lineno, item.texto))


def analizar_rutas(rutas: list[Path], config: ConfigCheck) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    for ruta in rutas:
        hallazgos.extend(analizar_ruta(ruta, config))
    return sorted(hallazgos, key=lambda item: (item.ruta_relativa, item.lineno, item.texto))


def renderizar_hallazgos(hallazgos: list[Hallazgo]) -> str:
    lineas = [
        f"[I18N_HARDCODE] {item.ruta_relativa}:{item.lineno} -> \"{item.texto}\""
        for item in hallazgos
    ]
    return "\n".join(lineas)



def _resolver_raiz_repo(ruta_base: Path) -> Path:
    partes = ruta_base.parts
    if len(partes) >= 2 and partes[-2:] == ("app", "ui"):
        return ruta_base.parent.parent
    if partes and partes[-1] == "presentacion":
        return ruta_base.parent
    return ruta_base.parent

def _analizar_archivo(archivo: Path, raiz_repo: Path, config: ConfigCheck) -> list[Hallazgo]:
    relativo = archivo.relative_to(raiz_repo).as_posix()
    if _ruta_excluida(relativo, config):
        return []

    modulo = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
    visitante = _VisitanteHardcode(ruta_relativa=relativo, config=config)
    return visitante.analizar(modulo)


def _ruta_excluida(relativo: str, config: ConfigCheck) -> bool:
    partes = set(relativo.split("/"))
    if any(parte in partes for parte in config.rutas_excluidas):
        return True
    return any(fnmatch.fnmatch(relativo, patron) for patron in config.archivos_excluidos)


def _es_docstring(node: ast.AST, padres: dict[ast.AST, ast.AST]) -> bool:
    parent = padres.get(node)
    if not isinstance(parent, ast.Expr):
        return False
    abuelo = padres.get(parent)
    if not isinstance(abuelo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    return bool(abuelo.body) and abuelo.body[0] is parent


def _en_contexto_logger(node: ast.AST, padres: dict[ast.AST, ast.AST], config: ConfigCheck) -> bool:
    actual = node
    while actual in padres:
        actual = padres[actual]
        if isinstance(actual, ast.Call):
            nombre = _nombre_llamada(actual.func)
            if nombre in config.metodos_logger or nombre in config.wrappers_logger_permitidos:
                return True
    return False


def _nombre_llamada(funcion: ast.AST) -> str | None:
    if isinstance(funcion, ast.Name):
        return funcion.id
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    return None


def _coincide_alguno(texto: str, patrones: tuple[str, ...]) -> bool:
    return any(re.fullmatch(patron, texto) for patron in patrones)


def _recortar_texto(texto: str, maximo: int) -> str:
    texto_limpio = " ".join(texto.split())
    if len(texto_limpio) <= maximo:
        return texto_limpio
    return f"{texto_limpio[: maximo - 1]}…"
