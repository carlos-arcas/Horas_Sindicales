from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

TOKENS_INGLES = {
    "adapter", "adapters", "application", "builder", "builders", "controller",
    "controllers", "core", "domain", "dto", "dtos", "entrypoint", "entrypoints",
    "handler", "helpers", "infrastructure", "mapper", "model", "models", "port",
    "ports", "presenter", "repository", "service", "services", "test", "tests",
    "ui", "use", "usecase", "usecases", "case", "view", "views", "widget", "worker",
}
PATRON_SIMBOLO_PUBLICO = re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
PATRON_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


@dataclass(frozen=True)
class HallazgoSimbolo:
    archivo: str
    simbolo: str
    tokens_ingles: tuple[str, ...]


def _partir_camel_case(texto: str) -> str:
    primer_pase = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", texto)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", primer_pase)


def _extraer_tokens(cadena: str) -> list[str]:
    normalizado = _partir_camel_case(cadena).replace("-", " ").replace("/", " ")
    return [bloque.lower() for bloque in re.split(r"[\s_.]+", normalizado) if bloque]


def _tokens_ingles_en_cadena(cadena: str) -> list[str]:
    return sorted({token for token in _extraer_tokens(cadena) if token in TOKENS_INGLES})


def _contar_tokens_ingles_en_texto(texto: str) -> int:
    return sum(
        sum(1 for token in _extraer_tokens(palabra) if token in TOKENS_INGLES)
        for palabra in PATRON_TOKEN.findall(texto)
    )


def _iterar_archivos_app(raiz: Path, carpeta_app: str):
    yield from sorted((raiz / carpeta_app).rglob("*.py"))


def listar_archivos_con_naming_ingles(raiz: Path, carpeta_app: str = "app") -> list[str]:
    hallazgos: list[str] = []
    for archivo in _iterar_archivos_app(raiz, carpeta_app):
        relativo = archivo.relative_to(raiz).as_posix()
        if _tokens_ingles_en_cadena(relativo):
            hallazgos.append(relativo)
    return hallazgos


def listar_simbolos_publicos_en_ingles(raiz: Path, carpeta_app: str = "app") -> list[HallazgoSimbolo]:
    hallazgos: list[HallazgoSimbolo] = []
    for archivo in _iterar_archivos_app(raiz, carpeta_app):
        relativo = archivo.relative_to(raiz).as_posix()
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            coincidencia = PATRON_SIMBOLO_PUBLICO.match(linea)
            if not coincidencia:
                continue
            simbolo = coincidencia.group(1)
            if simbolo.startswith("_"):
                continue
            tokens_ingles = _tokens_ingles_en_cadena(simbolo)
            if tokens_ingles:
                hallazgos.append(HallazgoSimbolo(relativo, simbolo, tuple(tokens_ingles)))
    return hallazgos


def ranking_offenders(raiz: Path, carpeta_app: str = "app", limite: int = 20) -> list[dict[str, int | str]]:
    puntajes: list[dict[str, int | str]] = []
    for archivo in _iterar_archivos_app(raiz, carpeta_app):
        relativo = archivo.relative_to(raiz).as_posix()
        contenido = archivo.read_text(encoding="utf-8")
        tokens_ruta = len(_tokens_ingles_en_cadena(relativo))
        tokens_texto = _contar_tokens_ingles_en_texto(contenido)
        total = tokens_ruta + tokens_texto
        if total <= 0:
            continue
        puntajes.append({
            "archivo": relativo,
            "tokens_ingles": total,
            "tokens_en_ruta": tokens_ruta,
            "tokens_en_codigo": tokens_texto,
        })
    return sorted(puntajes, key=lambda item: int(item["tokens_ingles"]), reverse=True)[:limite]


def construir_reporte(raiz: Path, umbral_offenders: int, carpeta_app: str = "app") -> dict:
    archivos_ingles = listar_archivos_con_naming_ingles(raiz, carpeta_app=carpeta_app)
    simbolos_ingles = listar_simbolos_publicos_en_ingles(raiz, carpeta_app=carpeta_app)
    total_offenders = len(archivos_ingles) + len(simbolos_ingles)
    return {
        "estado": "PASS" if total_offenders <= umbral_offenders else "FAIL",
        "umbral_offenders": umbral_offenders,
        "total_offenders": total_offenders,
        "archivos_con_naming_ingles": archivos_ingles,
        "simbolos_publicos_en_ingles": [
            {"archivo": item.archivo, "simbolo": item.simbolo, "tokens_ingles": list(item.tokens_ingles)}
            for item in simbolos_ingles
        ],
        "top_20_offenders": ranking_offenders(raiz, carpeta_app=carpeta_app, limite=20),
    }


def escribir_reportes(raiz: Path, reporte: dict) -> None:
    carpeta_logs = raiz / "logs"
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    (carpeta_logs / "naming_report.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lineas = [
        "# Reporte de naming debt", "", f"- Estado: **{reporte['estado']}**",
        f"- Umbral configurado: `{reporte['umbral_offenders']}`",
        f"- Total offenders detectados: `{reporte['total_offenders']}`", "",
        "## Archivos en app/ con naming en inglés",
    ]
    if reporte["archivos_con_naming_ingles"]:
        lineas.extend(f"- `{ruta}`" for ruta in reporte["archivos_con_naming_ingles"])
    else:
        lineas.append("- Ninguno")
    lineas.extend(["", "## Símbolos públicos en inglés"])
    simbolos = reporte["simbolos_publicos_en_ingles"]
    if simbolos:
        for item in simbolos:
            tokens = ", ".join(item["tokens_ingles"])
            lineas.append(f"- `{item['archivo']}` :: `{item['simbolo']}` ({tokens})")
    else:
        lineas.append("- Ninguno")
    lineas.extend(["", "## Top 20 offenders por archivo"])
    top = reporte["top_20_offenders"]
    if top:
        lineas.extend(["| Archivo | Tokens inglés | Ruta | Código |", "|---|---:|---:|---:|"])
        for item in top:
            lineas.append(
                "| {archivo} | {tokens_ingles} | {tokens_en_ruta} | {tokens_en_codigo} |".format(**item)
            )
    else:
        lineas.append("- Sin offenders")
    (carpeta_logs / "naming_report.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita naming debt español/inglés.")
    parser.add_argument("--umbral-offenders", type=int, default=0)
    parser.add_argument("--carpeta-app", default="app")
    parser.add_argument("--sin-escribir", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parsear_argumentos()
    raiz = Path(__file__).resolve().parents[1]
    reporte = construir_reporte(raiz=raiz, umbral_offenders=args.umbral_offenders, carpeta_app=args.carpeta_app)
    if not args.sin_escribir:
        escribir_reportes(raiz=raiz, reporte=reporte)
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
    return 0 if reporte["estado"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
