from __future__ import annotations

import ast
import re
from pathlib import Path

from app.application.auditoria_e2e.dto import CheckAuditoria, EstadoCheck, SeveridadCheck
from app.application.auditoria_e2e.puertos import SistemaArchivosPuerto


def evaluar_reglas_arquitectura(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    violations: list[str] = []
    for archivo in fs.listar_python(root / "app"):
        modulo = archivo.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        partes = modulo.split(".")
        if len(partes) < 3:
            continue
        capa = partes[1]
        if capa not in {"domain", "application", "infrastructure", "ui"}:
            continue

        tree = ast.parse(fs.leer_texto(archivo))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module] if node.module else []
            else:
                continue

            for imported in imports:
                if not imported:
                    continue
                if capa == "ui" and imported.startswith("app.infrastructure"):
                    violations.append(f"{archivo.relative_to(root)} -> {imported}")
                if capa == "domain" and imported.startswith("app.infrastructure"):
                    violations.append(f"{archivo.relative_to(root)} -> {imported}")
                if capa == "domain" and imported.startswith("app.ui"):
                    violations.append(f"{archivo.relative_to(root)} -> {imported}")

    estado = EstadoCheck.PASS if not violations else EstadoCheck.FAIL
    evidencia = ["Sin violaciones de imports UI->infra y domain->externo."] if not violations else violations
    return CheckAuditoria(
        id_check="CHECK-ARQ-001",
        estado=estado,
        severidad=SeveridadCheck.ALTO,
        evidencia=evidencia,
        recomendacion="Mantener dependencias dirigidas a puertos y casos de uso en application.",
    )


def evaluar_check_tests(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    pytest_ok = fs.existe(root / "requirements-dev.txt") and "pytest" in fs.leer_texto(root / "requirements-dev.txt")
    script_tests = root / "ejecutar_tests.bat"
    comando_ok = fs.existe(script_tests) and "pytest --cov=" in fs.leer_texto(script_tests)
    evidencia = [
        f"requirements-dev.txt con pytest={'sí' if pytest_ok else 'no'}",
        f"ejecutar_tests.bat con comando estándar={'sí' if comando_ok else 'no'}",
        "Cobertura dinámica no evaluada en auditoría estática.",
    ]

    if not pytest_ok or not comando_ok:
        estado = EstadoCheck.FAIL
    else:
        estado = EstadoCheck.NO_EVALUABLE

    return CheckAuditoria(
        id_check="CHECK-TEST-001",
        estado=estado,
        severidad=SeveridadCheck.MEDIO,
        evidencia=evidencia,
        recomendacion="Ejecutar pytest con cobertura en CI para convertir NO_EVALUABLE en PASS verificable.",
    )


def evaluar_check_logging(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    sin_prints = _sin_prints_en_codigo(fs, root)
    logging_cfg = fs.leer_texto(root / "app" / "bootstrap" / "logging.py") if fs.existe(root / "app" / "bootstrap" / "logging.py") else ""
    rotacion = "RotatingFileHandler" in logging_cfg
    crashes = "crashes.log" in logging_cfg

    evidencia = [
        f"Sin print en app/main={'sí' if sin_prints else 'no'}",
        f"Rotación configurada={'sí' if rotacion else 'no'}",
        f"crashes.log configurado={'sí' if crashes else 'no'}",
    ]
    estado = EstadoCheck.PASS if sin_prints and rotacion and crashes else EstadoCheck.FAIL
    return CheckAuditoria(
        id_check="CHECK-LOG-001",
        estado=estado,
        severidad=SeveridadCheck.ALTO,
        evidencia=evidencia,
        recomendacion="Canalizar salida por logging JSONL y evitar print().",
    )


def evaluar_check_windows_repro(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    lanzar = root / "lanzar_app.bat"
    tests = root / "ejecutar_tests.bat"
    req = root / "requirements.txt"
    req_dev = root / "requirements-dev.txt"
    ok = all(fs.existe(path) for path in [lanzar, tests, req, req_dev])
    pinneados = _requirements_pinneados(fs, req) and _requirements_pinneados(fs, req_dev)
    estado = EstadoCheck.PASS if ok and pinneados else EstadoCheck.FAIL
    evidencia = [f"Scripts windows presentes={'sí' if ok else 'no'}", f"Requirements pinneados={'sí' if pinneados else 'no'}"]
    return CheckAuditoria(
        id_check="CHECK-WIN-001",
        estado=estado,
        severidad=SeveridadCheck.MEDIO,
        evidencia=evidencia,
        recomendacion="Mantener scripts .bat y versiones pinneadas para reproducibilidad.",
    )


def evaluar_check_docs(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    requeridos = [
        "docs/arquitectura.md",
        "docs/decisiones_tecnicas.md",
        "docs/guia_pruebas.md",
        "docs/guia_logging.md",
        "docs/definicion_producto_final.md",
    ]
    faltantes = [ruta for ruta in requeridos if not fs.existe(root / ruta)]
    estado = EstadoCheck.PASS if not faltantes else EstadoCheck.FAIL
    evidencia = ["Docs mínimas presentes"] if not faltantes else [f"Falta {ruta}" for ruta in faltantes]
    return CheckAuditoria(
        id_check="CHECK-DOC-001",
        estado=estado,
        severidad=SeveridadCheck.BAJO,
        evidencia=evidencia,
        recomendacion="Mantener documentos mínimos actualizados en docs/.",
    )


def evaluar_check_versionado(fs: SistemaArchivosPuerto, root: Path) -> CheckAuditoria:
    version_path = root / "VERSION"
    changelog_path = root / "CHANGELOG.md"
    if not fs.existe(version_path) or not fs.existe(changelog_path):
        return CheckAuditoria(
            id_check="CHECK-VCS-001",
            estado=EstadoCheck.FAIL,
            severidad=SeveridadCheck.MEDIO,
            evidencia=["VERSION o CHANGELOG.md ausente"],
            recomendacion="Versionar con archivo VERSION y entrada correspondiente en CHANGELOG.",
        )

    version = fs.leer_texto(version_path).strip()
    changelog = fs.leer_texto(changelog_path)
    found = re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, flags=re.MULTILINE) is not None
    estado = EstadoCheck.PASS if found else EstadoCheck.FAIL
    evidencia = [f"VERSION={version}", f"Entrada en CHANGELOG={'sí' if found else 'no'}"]
    return CheckAuditoria(
        id_check="CHECK-VCS-001",
        estado=estado,
        severidad=SeveridadCheck.MEDIO,
        evidencia=evidencia,
        recomendacion="Sincronizar versión publicada con changelog versionado.",
    )


def _sin_prints_en_codigo(fs: SistemaArchivosPuerto, root: Path) -> bool:
    objetivos = [root / "main.py"]
    objetivos.extend(fs.listar_python(root / "app"))
    for archivo in objetivos:
        if not fs.existe(archivo):
            continue
        tree = ast.parse(fs.leer_texto(archivo), filename=str(archivo))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                return False
    return True


def _requirements_pinneados(fs: SistemaArchivosPuerto, ruta: Path) -> bool:
    if not fs.existe(ruta):
        return False
    pattern = re.compile(r"^[A-Za-z0-9_.\-\[\],]+==[A-Za-z0-9_.\-+!]+(?:\s*;\s*.+)?$")
    for line in fs.leer_texto(ruta).splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if trimmed.startswith("-r ") or trimmed.startswith("--"):
            continue
        if any(op in trimmed for op in (">=", "<=", "<", ">")):
            return False
        if not pattern.match(trimmed):
            return False
    return True
