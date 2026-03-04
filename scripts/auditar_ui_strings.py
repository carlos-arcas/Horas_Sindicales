from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical", "log"}
EVENT_HINTS = {"event", "metric", "audit", "telemetry", "span"}


@dataclass(frozen=True)
class HallazgoUIString:
    archivo: str
    linea: int
    columna: int
    literal: str

    @property
    def offender_id(self) -> str:
        return f"{self.archivo}:{self.linea}:{self.literal}"


def _iterar_archivos_ui(raiz: Path) -> list[Path]:
    base = raiz / "app" / "ui"
    return sorted(
        archivo
        for archivo in base.rglob("*.py")
        if "tests" not in archivo.parts and "copy_catalog" not in archivo.parts
    )


def _extraer_copy_keys(raiz: Path) -> set[str]:
    ruta = raiz / "app" / "ui" / "copy_catalog" / "catalogo.json"
    data = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return set()
    return {str(clave) for clave in data.keys()}


def _es_docstring(node: ast.Constant, parent: ast.AST | None) -> bool:
    if not isinstance(parent, ast.Expr):
        return False
    grandparent = getattr(parent, "_parent", None)
    if not isinstance(grandparent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    if not grandparent.body:
        return False
    return grandparent.body[0] is parent


def _nombre_llamada(call: ast.Call) -> str | None:
    fn = call.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def _es_contexto_excluido(node: ast.Constant, parent: ast.AST | None) -> bool:
    if parent is None:
        return False
    if _es_docstring(node, parent):
        return True

    if isinstance(parent, ast.Call):
        nombre = _nombre_llamada(parent)
        if nombre in LOG_METHODS:
            return True
        if nombre and any(hint in nombre.lower() for hint in EVENT_HINTS):
            return True

    return False


def _es_literal_sospechoso(texto: str, copy_keys: set[str]) -> bool:
    candidato = texto.strip()
    if not candidato or len(candidato) < 3:
        return False
    if candidato in copy_keys:
        return False
    if "\n" in candidato:
        return False
    if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", candidato):
        return False
    if any(token in candidato for token in (";", "{", "}")):
        return False
    if re.fullmatch(r"[A-Z0-9_]+", candidato):
        return False
    if re.fullmatch(r"[a-z0-9_.:-]+", candidato):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidato):
        if "_" in candidato or candidato.islower() or candidato.isupper():
            return False
        if re.search(r"[a-záéíóúñ][A-Z]", candidato):
            return False
        if re.fullmatch(r"[A-Z][a-záéíóúñ]+(?:[A-Z][A-Za-z0-9]+)+", candidato):
            return False
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", candidato):
        return False
    return True


def detectar_ui_strings_hardcoded(raiz: Path) -> list[HallazgoUIString]:
    copy_keys = _extraer_copy_keys(raiz)
    hallazgos: list[HallazgoUIString] = []

    for archivo in _iterar_archivos_ui(raiz):
        relativo = archivo.relative_to(raiz).as_posix()
        modulo = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)

        for parent in ast.walk(modulo):
            for child in ast.iter_child_nodes(parent):
                child._parent = parent  # type: ignore[attr-defined]

        for node in ast.walk(modulo):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            parent = getattr(node, "_parent", None)
            if _es_contexto_excluido(node, parent):
                continue
            if not _es_literal_sospechoso(node.value, copy_keys):
                continue

            hallazgos.append(
                HallazgoUIString(
                    archivo=relativo,
                    linea=node.lineno,
                    columna=node.col_offset,
                    literal=node.value.strip(),
                )
            )

    hallazgos.sort(key=lambda item: (item.archivo, item.linea, item.columna, item.literal))
    return hallazgos


def construir_reporte(raiz: Path) -> dict:
    offenders = detectar_ui_strings_hardcoded(raiz)
    return {
        "estado": "PASS" if not offenders else "WARN",
        "total_offenders": len(offenders),
        "offenders": [
            {
                "offender_id": item.offender_id,
                "archivo": item.archivo,
                "linea": item.linea,
                "columna": item.columna,
                "literal": item.literal,
            }
            for item in offenders
        ],
    }


def escribir_reportes(raiz: Path, reporte: dict) -> None:
    logs = raiz / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    (logs / "ui_strings_report.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lineas = [
        "# Auditoría de strings hardcoded en UI",
        "",
        f"- Estado: **{reporte['estado']}**",
        f"- Total offenders: `{reporte['total_offenders']}`",
        "",
        "## Offenders",
    ]

    offenders = reporte["offenders"]
    if offenders:
        lineas.extend(["| Archivo | Línea | Literal |", "|---|---:|---|"])
        for item in offenders:
            literal = item["literal"].replace("|", "\\|")
            lineas.append(f"| {item['archivo']} | {item['linea']} | `{literal}` |")
    else:
        lineas.append("- Sin offenders.")

    (logs / "ui_strings_report.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita strings hardcoded en app/ui.")
    parser.add_argument("--sin-escribir", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parsear_argumentos()
    raiz = Path(__file__).resolve().parents[1]
    reporte = construir_reporte(raiz)
    if not args.sin_escribir:
        escribir_reportes(raiz, reporte)
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
