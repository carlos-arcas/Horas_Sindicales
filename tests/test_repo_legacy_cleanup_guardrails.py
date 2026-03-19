from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "logs",
    "__pycache__",
    ".pytest_cache",
}
BINARY_SUFFIXES = {".png", ".ico", ".db", ".sqlite3", ".pyc", ".mo", ".zip", ".pdf"}
ALLOWLIST_TEXT = {
    Path("tests/test_repo_legacy_cleanup_guardrails.py"),
    Path("AGENTS.md"),
}
ALLOWLIST_NOMBRES = {
    Path("configuracion/i18n/_legacy_map.json"),
    Path("tests/application/test_confirmacion_pdf_legacy_wrappers_guardrail.py"),
    Path("tests/application/test_copy_catalog_puros.py"),
    Path("tests/ui_rules/test_copy_catalog.py"),
    Path("tests/test_repo_legacy_cleanup_guardrails.py"),
}
ALLOWLIST_PLACEHOLDERS = {
    Path("AUDITORIA.md"),
    Path("tests/test_root_auditoria_files_are_stubs.py"),
}
PATRONES_PROHIBIDOS = [
    re.compile(r"\bdjango\b", re.IGNORECASE),
    re.compile(r"next\.js", re.IGNORECASE),
    re.compile(r"\breact\b", re.IGNORECASE),
    re.compile(r"\bssr\b", re.IGNORECASE),
    re.compile(r"\bssg\b", re.IGNORECASE),
    re.compile(r"\bspa\b", re.IGNORECASE),
    re.compile(r"\bvercel\b", re.IGNORECASE),
    re.compile(r"aplicaci[oó]n web", re.IGNORECASE),
    re.compile(r"frontend web", re.IGNORECASE),
    re.compile(r"backend web", re.IGNORECASE),
    re.compile(r"api web", re.IGNORECASE),
]
PATRONES_NOMBRE_LEGACY = [
    re.compile(
        r"(^|[-_])(legacy|obsolete|deprecated|backup|bak|copy|copia|old|tmp)($|[-_.])",
        re.IGNORECASE,
    ),
]
PATRONES_PLACEHOLDER = [
    re.compile(r"^#.*(stub|placeholder)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"por completar", re.IGNORECASE),
    re.compile(r"todo[: ]+completar", re.IGNORECASE),
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"generado por ia", re.IGNORECASE),
]
ENTRYS_CANONICOS = [
    Path("main.py"),
    Path("app/__main__.py"),
    Path("lanzar_app.bat"),
    Path("launcher.bat"),
    Path("ejecutar_tests.bat"),
    Path("quality_gate.bat"),
    Path("scripts/gate_rapido.py"),
    Path("scripts/gate_pr.py"),
]
RUTAS_PROHIBIDAS = [
    Path("_backstage"),
]
ARCHIVOS_ELIMINADOS_PROHIBIDOS = [
    Path("docs/UX_SYNC_GUIDE.md"),
    Path("docs/api_sync_module.md"),
    Path("docs/docs_style_guide.md"),
    Path("docs/i18n_aliases_sin_linea.md"),
    Path("docs/naming_transicion.md"),
    Path("docs/quality_gate.md"),
    Path("docs/coverage_scope.md"),
    Path("scripts/gate_local.py"),
]


def _iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in IGNORE_PARTS for part in rel.parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        files.append(rel)
    return files


def test_no_reaparecen_referencias_a_stack_web_ajeno() -> None:
    offenders: list[str] = []
    for rel in _iter_repo_files():
        if rel in ALLOWLIST_TEXT:
            continue
        contenido = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        for patron in PATRONES_PROHIBIDOS:
            if patron.search(contenido):
                offenders.append(f"{rel.as_posix()} :: {patron.pattern}")
    assert not offenders, (
        "Se reintrodujeron referencias a stack incorrecto:\n" + "\n".join(offenders)
    )


def test_no_reaparecen_archivos_o_docs_con_naming_legacy_evidente() -> None:
    offenders: list[str] = []
    for rel in _iter_repo_files():
        if rel in ALLOWLIST_NOMBRES:
            continue
        for patron in PATRONES_NOMBRE_LEGACY:
            if patron.search(rel.name):
                offenders.append(rel.as_posix())
                break
    assert not offenders, (
        "Se detectaron archivos legacy/placeholders fuera del allowlist mínimo:\n"
        + "\n".join(offenders)
    )


def test_no_reaparecen_documentos_placeholder_inutiles() -> None:
    offenders: list[str] = []
    for rel in _iter_repo_files():
        if rel.suffix.lower() != ".md" or rel in ALLOWLIST_PLACEHOLDERS:
            continue
        contenido = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        for patron in PATRONES_PLACEHOLDER:
            if patron.search(contenido):
                offenders.append(f"{rel.as_posix()} :: {patron.pattern}")
    assert not offenders, (
        "Se detectó documentación placeholder o artificial fuera del allowlist contractual:\n"
        + "\n".join(offenders)
    )


def test_no_reaparecen_directorios_historicos_fuera_de_logs() -> None:
    offenders = [ruta.as_posix() for ruta in RUTAS_PROHIBIDAS if (ROOT / ruta).exists()]
    assert not offenders, "Persisten directorios históricos prohibidos: " + ", ".join(
        offenders
    )


def test_entrypoints_y_scripts_canonicos_siguen_existiendo() -> None:
    faltantes = [
        ruta.as_posix() for ruta in ENTRYS_CANONICOS if not (ROOT / ruta).exists()
    ]
    assert not faltantes, "Faltan entrypoints o scripts canónicos: " + ", ".join(
        faltantes
    )


def test_no_reaparecen_archivos_eliminados_por_limpieza() -> None:
    reintroducidos = [
        ruta.as_posix()
        for ruta in ARCHIVOS_ELIMINADOS_PROHIBIDOS
        if (ROOT / ruta).exists()
    ]
    assert not reintroducidos, (
        "Se reintrodujeron residuos eliminados en la limpieza de legacy: "
        + ", ".join(reintroducidos)
    )
