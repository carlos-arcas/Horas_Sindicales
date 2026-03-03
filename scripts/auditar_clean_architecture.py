from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

CAPAS = {
    "dominio": ("app/domain", "dominio"),
    "aplicacion": ("app/application", "aplicacion"),
    "infraestructura": ("app/infrastructure", "infraestructura"),
    "ui": ("app/ui", "presentacion"),
}
LIBRERIAS_SENSIBLES_UI = ("sqlite3", "reportlab", "sheets_client")
TOKENS_INFRA_UI = (
    "infraestructura",
    "repositorio",
    "repository",
    "provider",
    "proveedor",
)


def _ruta_a_modulo(relativo: Path) -> str:
    return ".".join(relativo.with_suffix("").parts)


def _capas_activas(raiz: Path) -> dict[str, tuple[str, ...]]:
    return {
        capa: tuple(ruta for ruta in rutas if (raiz / ruta).exists())
        for capa, rutas in CAPAS.items()
    }


def _prefixes_capa(capas: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    prefixes: dict[str, tuple[str, ...]] = {}
    for capa, rutas in capas.items():
        prefixes[capa] = tuple(ruta.replace("/", ".") for ruta in rutas)
    return prefixes


def _detectar_capa_modulo(
    modulo: str, prefixes: dict[str, tuple[str, ...]]
) -> str | None:
    for capa, prefijos in prefixes.items():
        if any(
            modulo == prefijo or modulo.startswith(f"{prefijo}.")
            for prefijo in prefijos
        ):
            return capa
    return None


def _archivos_python_en_rutas(raiz: Path, rutas: Iterable[str]) -> list[Path]:
    archivos: list[Path] = []
    for ruta in rutas:
        base = raiz / ruta
        if base.exists():
            archivos.extend(sorted(base.rglob("*.py")))
    return archivos


def _resolver_import_from(modulo_actual: str, modulo: str | None, nivel: int) -> str:
    if nivel == 0:
        return modulo or ""
    partes = modulo_actual.split(".")[:-1]
    base = partes[: max(len(partes) - (nivel - 1), 0)]
    if not modulo:
        return ".".join(base)
    return ".".join([*base, modulo]) if base else modulo


def _iterar_imports(archivo: Path, raiz: Path) -> list[dict[str, str | int]]:
    modulo_actual = _ruta_a_modulo(archivo.relative_to(raiz))
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    imports: list[dict[str, str | int]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            imports.extend(
                {"modulo": alias.name, "linea": nodo.lineno} for alias in nodo.names
            )
        if isinstance(nodo, ast.ImportFrom):
            modulo_destino = _resolver_import_from(
                modulo_actual, nodo.module, nodo.level
            )
            imports.append({"modulo": modulo_destino, "linea": nodo.lineno})
    return imports


def obtener_violaciones_imports(raiz: Path | None = None) -> list[dict]:
    base = raiz or Path(__file__).resolve().parents[1]
    capas = _capas_activas(base)
    prefixes = _prefixes_capa(capas)
    archivos = _archivos_python_en_rutas(
        base, [ruta for rutas in capas.values() for ruta in rutas]
    )
    violaciones: list[dict] = []
    for archivo in archivos:
        modulo_origen = _ruta_a_modulo(archivo.relative_to(base))
        capa_origen = _detectar_capa_modulo(modulo_origen, prefixes)
        if not capa_origen:
            continue
        for registro in _iterar_imports(archivo, base):
            modulo_destino = str(registro["modulo"])
            capa_destino = _detectar_capa_modulo(modulo_destino, prefixes)
            tipo = _tipo_violacion(capa_origen, capa_destino)
            if not tipo:
                continue
            violaciones.append(
                {
                    "tipo": tipo,
                    "archivo": archivo.relative_to(base).as_posix(),
                    "linea": int(registro["linea"]),
                    "modulo_origen": modulo_origen,
                    "modulo_destino": modulo_destino,
                    "capa_origen": capa_origen,
                    "capa_destino": capa_destino,
                }
            )
    return sorted(
        violaciones, key=lambda item: (item["archivo"], item["linea"], item["tipo"])
    )


def _tipo_violacion(capa_origen: str, capa_destino: str | None) -> str | None:
    if not capa_destino:
        return None
    if capa_origen == "ui" and capa_destino == "infraestructura":
        return "ui_importa_infraestructura"
    if capa_origen == "infraestructura" and capa_destino == "ui":
        return "infraestructura_importa_ui"
    if capa_origen == "dominio" and capa_destino != "dominio":
        return "dominio_importa_fuera_de_dominio"
    return None


def obtener_indicios_negocio_en_ui(raiz: Path | None = None) -> list[dict]:
    base = raiz or Path(__file__).resolve().parents[1]
    capas = _capas_activas(base)
    prefixes = _prefixes_capa(capas)
    ui_paths = capas.get("ui", ())
    indicios: list[dict] = []
    for archivo in _archivos_python_en_rutas(base, ui_paths):
        indicios.extend(_indicios_por_imports_ui(base, archivo, prefixes))
        indicios.extend(_indicios_por_ast_ui(base, archivo))
    return sorted(
        indicios, key=lambda item: (item["archivo"], item["linea"], item["tipo"])
    )


def _indicios_por_imports_ui(
    base: Path, archivo: Path, prefixes: dict[str, tuple[str, ...]]
) -> list[dict]:
    hallazgos: list[dict] = []
    for registro in _iterar_imports(archivo, base):
        modulo = str(registro["modulo"])
        modulo_min = modulo.lower()
        capa_destino = _detectar_capa_modulo(modulo, prefixes)
        if capa_destino == "infraestructura" or any(
            token in modulo_min for token in TOKENS_INFRA_UI
        ):
            hallazgos.append(
                _nuevo_indicio(
                    base,
                    archivo,
                    int(registro["linea"]),
                    "ui_importa_acceso_datos",
                    modulo,
                )
            )
        if any(
            modulo_min == lib or modulo_min.startswith(f"{lib}.")
            for lib in LIBRERIAS_SENSIBLES_UI
        ):
            hallazgos.append(
                _nuevo_indicio(
                    base,
                    archivo,
                    int(registro["linea"]),
                    "ui_usa_libreria_sensible",
                    modulo,
                )
            )
    return hallazgos


def _indicios_por_ast_ui(base: Path, archivo: Path) -> list[dict]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    hallazgos: list[dict] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = _nombre_callable(nodo.func).lower()
        total_args = len(nodo.args) + len(nodo.keywords)
        if (
            ("use_case" in nombre or "caso_de_uso" in nombre)
            and total_args >= 4
            and not _contiene_dto(nodo)
        ):
            detalle = f"{_nombre_callable(nodo.func)} con {total_args} argumentos"
            hallazgos.append(
                _nuevo_indicio(
                    base,
                    archivo,
                    nodo.lineno,
                    "ui_llama_use_case_grande_sin_dto",
                    detalle,
                )
            )
    return hallazgos


def _nombre_callable(funcion: ast.AST) -> str:
    if isinstance(funcion, ast.Name):
        return funcion.id
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    return "callable_desconocido"


def _contiene_dto(llamada: ast.Call) -> bool:
    for arg in llamada.args:
        if isinstance(arg, ast.Name) and "dto" in arg.id.lower():
            return True
    for kw in llamada.keywords:
        if kw.arg and "dto" in kw.arg.lower():
            return True
        if isinstance(kw.value, ast.Name) and "dto" in kw.value.id.lower():
            return True
    return False


def _nuevo_indicio(
    base: Path, archivo: Path, linea: int, tipo: str, detalle: str
) -> dict:
    return {
        "tipo": tipo,
        "archivo": archivo.relative_to(base).as_posix(),
        "linea": linea,
        "detalle": detalle,
    }


def generar_reporte_json(violaciones: list[dict], indicios: list[dict]) -> dict:
    return {
        "estado": "PASS" if not violaciones else "FAIL",
        "total_violaciones": len(violaciones),
        "total_indicios_ui": len(indicios),
        "violaciones": violaciones,
        "indicios_negocio_en_ui": indicios,
    }


def generar_reporte_md(violaciones: list[dict], indicios: list[dict]) -> str:
    lineas = [
        "# Auditoría de Clean Architecture",
        "",
        f"- Violaciones de dependencias: **{len(violaciones)}**",
        f"- Indicios de negocio en UI: **{len(indicios)}**",
        "",
        "## Violaciones de imports entre capas",
    ]
    if violaciones:
        lineas.extend(
            ["| Tipo | Archivo | Línea | Origen | Destino |", "|---|---|---:|---|---|"]
        )
        for item in violaciones:
            lineas.append(
                f"| {item['tipo']} | `{item['archivo']}` | {item['linea']} | "
                f"`{item['modulo_origen']}` | `{item['modulo_destino']}` |"
            )
    else:
        lineas.append("- Sin violaciones detectadas.")
    lineas.append("")
    lineas.append("## Indicios de negocio en UI")
    if indicios:
        lineas.extend(["| Tipo | Archivo | Línea | Detalle |", "|---|---|---:|---|"])
        for item in indicios:
            lineas.append(
                f"| {item['tipo']} | `{item['archivo']}` | {item['linea']} | {item['detalle']} |"
            )
    else:
        lineas.append("- Sin indicios detectados.")
    return "\n".join(lineas) + "\n"


def _escribir_reporte(raiz: Path, reporte_json: dict, reporte_md: str) -> None:
    ruta_md = raiz / "docs" / "auditoria_clean_architecture.md"
    ruta_json = raiz / "logs" / "auditoria_clean_architecture.json"
    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    ruta_md.write_text(reporte_md, encoding="utf-8")
    ruta_json.write_text(
        json.dumps(reporte_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    raiz = Path(__file__).resolve().parents[1]
    violaciones = obtener_violaciones_imports(raiz)
    indicios = obtener_indicios_negocio_en_ui(raiz)
    reporte_json = generar_reporte_json(violaciones, indicios)
    reporte_md = generar_reporte_md(violaciones, indicios)
    _escribir_reporte(raiz, reporte_json, reporte_md)
    logger.info(
        "auditoria_clean_architecture_generada",
        extra={"violaciones": len(violaciones), "indicios": len(indicios)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
