from __future__ import annotations

import argparse
import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_WINDOW_DIR = ROOT / "app" / "ui" / "vistas" / "main_window"


@dataclass(frozen=True)
class Hallazgo:
    archivo: str
    linea: int
    valor: str


def _run_git(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def _resolver_base_ref() -> str:
    candidatos = ["main", "master"]
    for candidato in candidatos:
        resultado = _run_git(["git", "merge-base", "HEAD", candidato])
        if resultado.returncode == 0:
            sha = resultado.stdout.strip()
            if sha:
                return sha
    return "HEAD~1"


def _listar_modulos_nuevos(ruta_objetivo: Path) -> list[Path]:
    if not ruta_objetivo.exists():
        return []

    base_ref = _resolver_base_ref()
    objetivo_rel = ruta_objetivo.relative_to(ROOT).as_posix()
    resultado = _run_git(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=A",
            f"{base_ref}..HEAD",
            "--",
            objetivo_rel,
        ]
    )
    if resultado.returncode != 0:
        return []

    modulos: list[Path] = []
    for linea in resultado.stdout.splitlines():
        ruta_rel = linea.strip()
        if not ruta_rel.endswith(".py"):
            continue
        ruta_absoluta = ROOT / ruta_rel
        if ruta_absoluta.exists():
            modulos.append(ruta_absoluta)
    return sorted(modulos)


def _es_docstring(nodo: ast.AST, padres: dict[ast.AST, ast.AST]) -> bool:
    padre = padres.get(nodo)
    if not isinstance(padre, ast.Expr):
        return False

    abuelo = padres.get(padre)
    if isinstance(abuelo, ast.Module):
        return bool(abuelo.body) and abuelo.body[0] is padre
    if isinstance(abuelo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return bool(abuelo.body) and abuelo.body[0] is padre
    return False


def _es_clave_catalogo(nodo: ast.Constant, padres: dict[ast.AST, ast.AST]) -> bool:
    padre = padres.get(nodo)
    if not isinstance(padre, ast.Call):
        return False

    funcion = padre.func
    if isinstance(funcion, ast.Name):
        nombre = funcion.id
    elif isinstance(funcion, ast.Attribute):
        nombre = funcion.attr
    else:
        return False

    return nombre in {"copy_text", "copy_html", "copy_format"}


def _es_string_ui(valor: str) -> bool:
    texto = valor.strip()
    if not texto:
        return False
    if len(texto) < 3:
        return False
    if texto.startswith(("http://", "https://", "qrc:/", "#")):
        return False
    return any(caracter.isalpha() for caracter in texto)


def _hallazgos_en_archivo(path: Path) -> list[Hallazgo]:
    arbol = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    padres: dict[ast.AST, ast.AST] = {}
    for nodo in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(nodo):
            padres[hijo] = nodo

    hallazgos: list[Hallazgo] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Constant) or not isinstance(nodo.value, str):
            continue
        if _es_docstring(nodo, padres) or _es_clave_catalogo(nodo, padres):
            continue
        if not _es_string_ui(nodo.value):
            continue
        hallazgos.append(
            Hallazgo(
                archivo=path.relative_to(ROOT).as_posix(),
                linea=getattr(nodo, "lineno", 0),
                valor=nodo.value.strip(),
            )
        )
    return hallazgos


def auditar_scope(scope: str) -> dict[str, object]:
    if scope != "main_window":
        raise ValueError(f"Scope no soportado: {scope}")

    modulos_nuevos = _listar_modulos_nuevos(MAIN_WINDOW_DIR)
    hallazgos: list[Hallazgo] = []
    for modulo in modulos_nuevos:
        hallazgos.extend(_hallazgos_en_archivo(modulo))

    return {
        "scope": scope,
        "estado": "PASS" if not hallazgos else "FAIL",
        "modulos_nuevos_analizados": [p.relative_to(ROOT).as_posix() for p in modulos_nuevos],
        "total_hallazgos": len(hallazgos),
        "hallazgos": [
            {"archivo": h.archivo, "linea": h.linea, "valor": h.valor}
            for h in sorted(hallazgos, key=lambda item: (item.archivo, item.linea, item.valor))
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita strings hardcodeadas de UI.")
    parser.add_argument("--scope", default="main_window", choices=["main_window"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    reporte = auditar_scope(args.scope)
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
    return 0 if reporte["estado"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
