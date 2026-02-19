#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "auditoria_producto.md"
RULES_PATH = ROOT / ".config" / "product_audit_rules.json"
QUALITY_GATE_PATH = ROOT / ".config" / "quality_gate.json"
IGNORE_DIRS = {
    ".venv",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}


@dataclass(frozen=True)
class AreaResult:
    name: str
    weight: int
    score: int
    formula: str


@dataclass(frozen=True)
class Improvement:
    area: str
    action: str
    area_gain: int
    weighted_gain: float


def default_rules() -> dict[str, Any]:
    return {
        "weights": {
            "Arquitectura estructural": 20,
            "Testing & cobertura": 20,
            "Complejidad accidental": 15,
            "DevEx / CI / Governance": 15,
            "Observabilidad y resiliencia": 10,
            "Configuración & seguridad": 10,
            "Documentación & gobernanza": 10,
        },
        "caps": {
            "Arquitectura estructural": 100,
            "Testing & cobertura": 100,
            "Complejidad accidental": 100,
            "DevEx / CI / Governance": 100,
            "Observabilidad y resiliencia": 100,
            "Configuración & seguridad": 100,
            "Documentación & gobernanza": 100,
        },
        "architecture": {
            "base": 100,
            "penalty_per_module_over_500": 5,
            "penalty_per_module_over_800": 2,
            "penalty_per_violation": 10,
            "penalty_whitelist_active": 8,
        },
        "testing": {
            "base": 60,
            "coverage_growth_per_point": 0.9,
            "tests_count_bonus_threshold": 100,
            "tests_count_bonus": 5,
            "coverage_shortfall_penalty_per_point": 1.2,
        },
        "complexity": {
            "base": 100,
            "max_file_lines_penalty_divisor": 120,
            "penalty_per_module_over_500": 3,
            "penalty_per_module_over_800": 3,
        },
        "devex": {
            "base": 50,
            "ci_green_bonus": 20,
            "release_automated_bonus": 15,
            "threshold_alignment_bonus": 15,
        },
        "observability": {
            "base": 60,
            "correlation_id_bonus": 20,
            "structured_logs_bonus": 20,
            "main_window_over_500_penalty": 10,
        },
        "security": {
            "base": 55,
            "secrets_outside_repo_bonus": 35,
            "db_in_repo_root_penalty": 12,
            "has_env_example_bonus": 10,
        },
        "documentation": {
            "base": 20,
            "has_contributing_bonus": 30,
            "has_changelog_bonus": 20,
            "has_dod_bonus": 20,
            "has_roadmap_bonus": 10,
        },
        "calibration": {
            "enabled": True,
            "notes": "Ajusta pesos, bases y penalizaciones sin tocar código.",
        },
    }


def load_rules() -> dict[str, Any]:
    defaults = default_rules()
    if not RULES_PATH.exists():
        return defaults
    try:
        loaded = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    merged = defaults.copy()
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "si", "sí"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Valor booleano inválido: {value!r}")


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Valor entero inválido: {value!r}") from exc


def parse_float(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Valor float inválido: {value!r}") from exc


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "."
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, env=env)


def git_short_commit() -> str:
    result = run_command(["git", "rev-parse", "--short", "HEAD"])
    return result.stdout.strip() or "N/D"


def clamp_to_score(value: float, cap: int = 100) -> int:
    return max(0, min(cap, int(round(value))))


def find_file(names: tuple[str, ...]) -> bool:
    return any((ROOT / name).exists() for name in names)


def read_coverage_threshold() -> tuple[int | None, list[str], bool]:
    evidences: list[str] = []
    thresholds: list[tuple[int, str]] = []

    if QUALITY_GATE_PATH.exists():
        try:
            config = json.loads(QUALITY_GATE_PATH.read_text(encoding="utf-8"))
            if isinstance(config.get("coverage_fail_under"), (int, float)):
                value = int(config["coverage_fail_under"])
                thresholds.append((value, ".config/quality_gate.json:coverage_fail_under"))
                evidences.append(f".config/quality_gate.json -> coverage_fail_under={value}")
        except Exception:
            evidences.append(".config/quality_gate.json -> no legible")

    regex = re.compile(r"--cov-fail-under(?:=|\s+)(\d+)")
    for rel in ["Makefile", "pyproject.toml", "tox.ini", "scripts", ".github/workflows"]:
        target = ROOT / rel
        if not target.exists():
            continue
        files = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file()]
        for file in files:
            if should_ignore(file.relative_to(ROOT)):
                continue
            text = file.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = regex.search(line)
                if match:
                    value = int(match.group(1))
                    src = f"{file.relative_to(ROOT).as_posix()}:{lineno}"
                    thresholds.append((value, src))
                    evidences.append(f"{src} -> --cov-fail-under {value}")

    if not thresholds:
        return None, evidences, False

    values = {v for v, _ in thresholds}
    aligned = len(values) == 1
    chosen = thresholds[0][0]
    return chosen, evidences, aligned


def collect_py_file_stats() -> tuple[int, str, list[dict[str, Any]], int, int]:
    top: list[dict[str, Any]] = []
    max_lines = 0
    max_path = "N/D"
    over_500 = 0
    over_800 = 0

    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if should_ignore(rel):
            continue
        lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        top.append({"path": rel.as_posix(), "lines": lines})
        if lines > max_lines:
            max_lines = lines
            max_path = rel.as_posix()
        if lines > 500:
            over_500 += 1
        if lines > 800:
            over_800 += 1

    top_sorted = sorted(top, key=lambda item: item["lines"], reverse=True)[:10]
    return max_lines, max_path, top_sorted, over_500, over_800


def detect_whitelist_evidence() -> tuple[bool, list[str]]:
    test_file = ROOT / "tests" / "test_architecture_imports.py"
    if not test_file.exists():
        return False, []
    patterns = ["ALLOWLIST", "WHITELIST", "allowed_imports", "exceptions", "TEMP", "sqlite3", "gspread", "ALLOWED_VIOLATIONS"]
    evidences: list[str] = []
    content = test_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    whitelist_active = False
    for idx, line in enumerate(content, start=1):
        if "ALLOWED_VIOLATIONS" in line and "=" in line:
            whitelist_active = "set()" not in line.replace(" ", "")
        if any(p.lower() in line.lower() for p in patterns):
            evidences.append(f"tests/test_architecture_imports.py:{idx}: {line.strip()}")
    return whitelist_active, evidences


def parse_architecture_violations(output: str) -> int:
    matches = re.findall(r"Archivo origen:", output)
    if matches:
        return len(matches)
    fallback = re.search(r"(\d+) failed", output)
    if fallback:
        return int(fallback.group(1))
    return 0


def parse_test_count(output: str) -> int:
    match = re.search(r"collected\s+(\d+)\s+items", output)
    if match:
        return int(match.group(1))
    alt = re.search(r"(\d+)\s+tests?\s+collected", output)
    return int(alt.group(1)) if alt else 0


def parse_total_coverage(output: str) -> float | None:
    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
    if match:
        return float(match.group(1))
    alt = re.search(r"TOTAL\s+.*?(\d+(?:\.\d+)?)%", output)
    return float(alt.group(1)) if alt else None


def find_secret_files() -> list[str]:
    found: list[str] = []
    candidates = [ROOT / ".env", ROOT / "credentials.json", ROOT / "token.json"]
    candidates.extend((ROOT / "app").glob("*.pem") if (ROOT / "app").exists() else [])
    candidates.extend(ROOT.glob("*.pem"))
    for item in candidates:
        if item.exists():
            found.append(item.relative_to(ROOT).as_posix())
    return sorted(set(found))


def find_db_files_in_root() -> list[str]:
    db_patterns = ("*.db", "*.sqlite", "*.sqlite3", "*.db3")
    paths: list[str] = []
    for pattern in db_patterns:
        for file in ROOT.glob(pattern):
            if file.is_file():
                paths.append(file.name)
    return sorted(set(paths))


def auto_collect(args: argparse.Namespace) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "warnings": [],
        "evidences": {
            "architecture": [],
            "complexity": [],
            "security": [],
            "coverage": [],
        },
    }

    max_lines, max_path, top10, over500, over800 = collect_py_file_stats()
    metrics.update(
        {
            "max_file_lines": max_lines,
            "max_file_path": max_path,
            "top_10_files": top10,
            "critical_modules_over_500": over500,
            "modules_over_800": over800,
            "main_window_lines": 0,
            "use_cases_lines": 0,
        }
    )
    metrics["evidences"]["complexity"] = [f"{item['path']} -> {item['lines']} líneas" for item in top10]

    threshold, threshold_evidences, aligned = read_coverage_threshold()
    metrics["coverage_threshold"] = threshold or 0
    metrics["coverage_thresholds_aligned"] = aligned
    metrics["evidences"]["coverage"].extend(threshold_evidences)

    whitelist_active, whitelist_evidence = detect_whitelist_evidence()
    metrics["whitelist_active"] = whitelist_active
    metrics["evidences"]["architecture"].extend(whitelist_evidence)

    arch_test = ROOT / "tests" / "test_architecture_imports.py"
    architecture_violations = 0
    if arch_test.exists():
        cmd = ["pytest", "-q", "tests/test_architecture_imports.py"]
        result = run_command(cmd)
        combined = f"{result.stdout}\n{result.stderr}"
        architecture_violations = parse_architecture_violations(combined) if result.returncode != 0 else 0
        metrics["evidences"]["architecture"].append(f"Comando: PYTHONPATH=. {' '.join(cmd)}")
        metrics["evidences"]["architecture"].append(combined.strip() or "Sin salida")
    metrics["architecture_violations"] = architecture_violations

    collect_cmd = ["pytest", "-q", "--collect-only"]
    collected = run_command(collect_cmd)
    collected_output = f"{collected.stdout}\n{collected.stderr}"
    metrics["tests_count"] = parse_test_count(collected_output)

    cov_cmd = ["pytest", "-q", "--cov=app", "--cov-report=term-missing"]
    cov_result = run_command(cov_cmd)
    cov_out = f"{cov_result.stdout}\n{cov_result.stderr}"
    coverage = parse_total_coverage(cov_out)
    if coverage is None and ("unrecognized arguments" in cov_out.lower() or "--cov" in cov_out.lower()):
        metrics["warnings"].append("No se pudo calcular coverage real porque falta pytest-cov.")
    elif coverage is None:
        metrics["warnings"].append("No se pudo parsear el TOTAL de cobertura.")
    metrics["coverage"] = coverage
    metrics["evidences"]["coverage"].append(f"Comando: PYTHONPATH=. {' '.join(cov_cmd)}")
    metrics["evidences"]["coverage"].append(cov_out.strip() or "Sin salida")

    secret_files = find_secret_files()
    metrics["secrets_outside_repo"] = len(secret_files) == 0
    metrics["secret_paths"] = secret_files
    metrics["evidences"]["security"].extend(secret_files or ["No se detectaron secretos en repo root/app"])

    db_files = find_db_files_in_root()
    metrics["db_in_repo_root"] = len(db_files) > 0
    metrics["db_paths"] = db_files
    metrics["evidences"]["security"].extend(db_files or ["No se detectaron DB en raíz"])

    metrics["has_env_example"] = (ROOT / ".env.example").exists()
    metrics["has_contributing"] = find_file(("CONTRIBUTING.md", "CONTRIBUTING"))
    metrics["has_changelog"] = find_file(("CHANGELOG.md", "CHANGELOG"))
    metrics["has_dod"] = (ROOT / "docs" / "definition_of_done.md").exists() or any(
        "dod" in p.name.lower() for p in (ROOT / "docs").glob("*.md")
    )
    metrics["has_roadmap"] = find_file(("ROADMAP.md", "docs/roadmap.md"))

    metrics["ci_green"] = args.ci_green
    metrics["release_automated"] = args.release_automated
    metrics["correlation_id_implemented"] = args.correlation_id_implemented
    metrics["structured_logs"] = args.structured_logs
    return metrics


def score_areas(metrics: dict[str, Any], rules: dict[str, Any]) -> tuple[list[AreaResult], list[Improvement], float]:
    improvements: list[Improvement] = []
    weights = rules["weights"]
    caps = rules["caps"]

    a = rules["architecture"]
    arch_penalty = (
        metrics["critical_modules_over_500"] * a["penalty_per_module_over_500"]
        + metrics["modules_over_800"] * a["penalty_per_module_over_800"]
        + metrics["architecture_violations"] * a["penalty_per_violation"]
        + (a["penalty_whitelist_active"] if metrics["whitelist_active"] else 0)
    )
    architecture_score = clamp_to_score(a["base"] - arch_penalty, caps["Arquitectura estructural"])

    t = rules["testing"]
    coverage = metrics.get("coverage") or 0.0
    threshold = metrics.get("coverage_threshold") or 0
    testing_score = t["base"] + max(0.0, coverage - threshold) * t["coverage_growth_per_point"]
    if coverage < threshold:
        testing_score -= (threshold - coverage) * t["coverage_shortfall_penalty_per_point"]
    if metrics["tests_count"] >= t["tests_count_bonus_threshold"]:
        testing_score += t["tests_count_bonus"]
    testing_score = clamp_to_score(testing_score, caps["Testing & cobertura"])

    c = rules["complexity"]
    complexity_penalty = round(metrics["max_file_lines"] / c["max_file_lines_penalty_divisor"]) + (
        metrics["critical_modules_over_500"] * c["penalty_per_module_over_500"]
    ) + (metrics["modules_over_800"] * c["penalty_per_module_over_800"])
    complexity_score = clamp_to_score(c["base"] - complexity_penalty, caps["Complejidad accidental"])

    d = rules["devex"]
    devex_score = d["base"]
    devex_score += d["ci_green_bonus"] if metrics["ci_green"] else 0
    devex_score += d["release_automated_bonus"] if metrics["release_automated"] else 0
    devex_score += d["threshold_alignment_bonus"] if metrics["coverage_thresholds_aligned"] else 0
    devex_score = clamp_to_score(devex_score, caps["DevEx / CI / Governance"])

    o = rules["observability"]
    observability_score = o["base"]
    observability_score += o["correlation_id_bonus"] if metrics["correlation_id_implemented"] else 0
    observability_score += o["structured_logs_bonus"] if metrics["structured_logs"] else 0
    if metrics["main_window_lines"] > 500:
        observability_score -= o["main_window_over_500_penalty"]
    observability_score = clamp_to_score(observability_score, caps["Observabilidad y resiliencia"])

    s = rules["security"]
    security_score = s["base"]
    security_score += s["secrets_outside_repo_bonus"] if metrics["secrets_outside_repo"] else 0
    security_score += s["has_env_example_bonus"] if metrics["has_env_example"] else 0
    if metrics["db_in_repo_root"]:
        security_score -= s["db_in_repo_root_penalty"]
    security_score = clamp_to_score(security_score, caps["Configuración & seguridad"])

    g = rules["documentation"]
    doc_score = g["base"]
    doc_score += g["has_contributing_bonus"] if metrics["has_contributing"] else 0
    doc_score += g["has_changelog_bonus"] if metrics["has_changelog"] else 0
    doc_score += g["has_dod_bonus"] if metrics["has_dod"] else 0
    doc_score += g["has_roadmap_bonus"] if metrics["has_roadmap"] else 0
    doc_score = clamp_to_score(doc_score, caps["Documentación & gobernanza"])

    area_scores = {
        "Arquitectura estructural": (architecture_score, f"base {a['base']} - penalties {arch_penalty}"),
        "Testing & cobertura": (testing_score, f"base {t['base']} cov={coverage:.2f} threshold={threshold}"),
        "Complejidad accidental": (complexity_score, f"base {c['base']} - penalties {complexity_penalty}"),
        "DevEx / CI / Governance": (devex_score, f"base {d['base']} + bonuses"),
        "Observabilidad y resiliencia": (observability_score, f"base {o['base']} + bonuses"),
        "Configuración & seguridad": (security_score, f"base {s['base']} + bonuses/penalties"),
        "Documentación & gobernanza": (doc_score, f"base {g['base']} + bonuses"),
    }

    areas = [AreaResult(name, weights[name], score, formula) for name, (score, formula) in area_scores.items()]

    for area in areas:
        if area.score < 100:
            gap = 100 - area.score
            improvements.append(Improvement(area.name, f"Cerrar brecha de {gap} puntos", gap, gap * (area.weight / 100)))

    weighted_global = sum(a.score * (a.weight / 100) for a in areas)
    return areas, improvements, weighted_global


def compute_trend(current_snapshot: dict[str, Any], previous_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not previous_snapshot:
        return {"message": "No existe auditoría previa para calcular tendencia.", "delta": None, "improvements": [], "regressions": []}
    current_areas = {item["name"]: item["score"] for item in current_snapshot["areas"]}
    prev_areas = {item["name"]: item["score"] for item in previous_snapshot.get("areas", [])}
    deltas = []
    for name, score in current_areas.items():
        old = prev_areas.get(name)
        if old is None:
            continue
        deltas.append({"area": name, "delta": score - old})
    improvements = sorted([d for d in deltas if d["delta"] > 0], key=lambda x: x["delta"], reverse=True)[:3]
    regressions = sorted([d for d in deltas if d["delta"] < 0], key=lambda x: x["delta"])[:3]
    return {
        "message": "Tendencia calculada contra auditoría previa.",
        "delta": round(current_snapshot["global_score"] - previous_snapshot.get("global_score", 0), 2),
        "improvements": improvements,
        "regressions": regressions,
    }


def load_previous_snapshot() -> dict[str, Any] | None:
    audit_dir = ROOT / "docs" / "audits"
    if not audit_dir.exists():
        return None
    files = sorted(audit_dir.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def render_markdown(snapshot: dict[str, Any], trend: dict[str, Any]) -> str:
    metrics = snapshot["metrics"]
    areas = snapshot["areas"]
    improvements = snapshot["improvements"]
    evidences = metrics.get("evidences", {})

    metrics_rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in metrics.items() if k not in {"evidences", "warnings", "top_10_files"})
    scores_rows = "\n".join(
        f"| {a['name']} | {a['weight']}% | {a['score']} | {a['score'] * (a['weight'] / 100):.2f} | {a['formula']} |"
        for a in areas
    )
    top_files = "\n".join(f"- `{item['path']}`: {item['lines']} líneas" for item in metrics.get("top_10_files", []))
    if not top_files:
        top_files = "- Sin datos"
    plan_rows = "\n".join(
        f"{i}. **[{item['area']}]** {item['action']} (impacto área: +{item['area_gain']}, impacto global: +{item['weighted_gain']:.2f})."
        for i, item in enumerate(improvements[:5], start=1)
    )
    warnings = "\n".join(f"- ⚠️ {w}" for w in metrics.get("warnings", [])) or "- Sin warnings"
    trend_improvements = "\n".join(f"- {i['area']}: +{i['delta']}" for i in trend.get("improvements", [])) or "- N/A"
    trend_regressions = "\n".join(f"- {i['area']}: {i['delta']}" for i in trend.get("regressions", [])) or "- N/A"

    return f"""# Auditoría técnica cuantitativa

- **Fecha:** {snapshot['timestamp']}
- **Commit:** `{snapshot['commit']}`

## Métricas base

| Métrica | Valor |
|---|---|
{metrics_rows}

## Score por áreas

| Área | Peso | Score (0-100) | Aporte ponderado | Cálculo |
|---|---:|---:|---:|---|
{scores_rows}

## Score global ponderado

**{snapshot['global_score']:.2f} / 100**

## Plan priorizado (Top 5)

{plan_rows or '1. No hay acciones pendientes.'}

## Evidencias

### Arquitectura
{chr(10).join(f'- {e}' for e in evidences.get('architecture', [])) or '- Sin evidencia'}

### Complejidad
{top_files}

### Seguridad
{chr(10).join(f'- {e}' for e in evidences.get('security', [])) or '- Sin evidencia'}

### Coverage
{chr(10).join(f'- {e}' for e in evidences.get('coverage', [])) or '- Sin evidencia'}

## Tendencia
- {trend.get('message')}
- Score global actual vs anterior: {snapshot['global_score']:.2f} vs {('N/A' if trend.get('delta') is None else f"{snapshot['global_score'] - trend['delta']:.2f}")} (delta: {trend.get('delta', 'N/A')})
- Top 3 mejoras:
{trend_improvements}
- Top 3 regresiones:
{trend_regressions}

## Warnings
{warnings}
"""


def build_snapshot(args: argparse.Namespace, rules: dict[str, Any]) -> dict[str, Any]:
    if args.auto:
        metrics = auto_collect(args)
    else:
        metrics = {
            "coverage": args.coverage,
            "max_file_lines": args.max_file_lines,
            "main_window_lines": args.main_window_lines,
            "use_cases_lines": args.use_cases_lines,
            "architecture_violations": args.architecture_violations,
            "ci_green": args.ci_green,
            "release_automated": args.release_automated,
            "whitelist_active": args.whitelist_active,
            "tests_count": args.tests_count,
            "critical_modules_over_500": args.critical_modules_over_500,
            "modules_over_800": args.modules_over_800,
            "coverage_thresholds_aligned": args.coverage_thresholds_aligned,
            "coverage_threshold": args.coverage_threshold,
            "correlation_id_implemented": args.correlation_id_implemented,
            "structured_logs": args.structured_logs,
            "secrets_outside_repo": args.secrets_outside_repo,
            "db_in_repo_root": args.db_in_repo_root,
            "has_env_example": args.has_env_example,
            "has_contributing": args.has_contributing,
            "has_changelog": args.has_changelog,
            "has_dod": args.has_dod,
            "has_roadmap": args.has_roadmap,
            "warnings": [],
            "evidences": {"architecture": [], "complexity": [], "security": [], "coverage": []},
            "top_10_files": [],
            "max_file_path": "N/D",
            "secret_paths": [],
            "db_paths": [],
        }

    areas, improvements, weighted_global = score_areas(metrics, rules)
    return {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "commit": git_short_commit(),
        "metrics": metrics,
        "areas": [a.__dict__ for a in areas],
        "improvements": [i.__dict__ for i in sorted(improvements, key=lambda x: x.weighted_gain, reverse=True)],
        "global_score": round(weighted_global, 2),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auditor técnico cuantitativo de producto")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--out", default=str(DOC_PATH))
    parser.add_argument("--json-out", default="")

    parser.add_argument("--coverage", type=parse_float, default=0.0)
    parser.add_argument("--coverage-threshold", type=parse_int, default=63)
    parser.add_argument("--max-file-lines", type=parse_int, default=0)
    parser.add_argument("--main-window-lines", type=parse_int, default=0)
    parser.add_argument("--use-cases-lines", type=parse_int, default=0)
    parser.add_argument("--architecture-violations", type=parse_int, default=0)
    parser.add_argument("--ci-green", type=parse_bool, default=True)
    parser.add_argument("--release-automated", type=parse_bool, default=True)
    parser.add_argument("--whitelist-active", type=parse_bool, default=False)
    parser.add_argument("--tests-count", type=parse_int, default=0)
    parser.add_argument("--critical-modules-over-500", type=parse_int, default=0)
    parser.add_argument("--modules-over-800", type=parse_int, default=0)
    parser.add_argument("--coverage-thresholds-aligned", type=parse_bool, default=True)
    parser.add_argument("--correlation-id-implemented", type=parse_bool, default=True)
    parser.add_argument("--structured-logs", type=parse_bool, default=True)
    parser.add_argument("--secrets-outside-repo", type=parse_bool, default=True)
    parser.add_argument("--db-in-repo-root", type=parse_bool, default=False)
    parser.add_argument("--has-env-example", type=parse_bool, default=(ROOT / ".env.example").exists())
    parser.add_argument("--has-contributing", type=parse_bool, default=find_file(("CONTRIBUTING.md", "CONTRIBUTING")))
    parser.add_argument("--has-changelog", type=parse_bool, default=find_file(("CHANGELOG.md", "CHANGELOG")))
    parser.add_argument("--has-dod", type=parse_bool, default=(ROOT / "docs" / "definition_of_done.md").exists())
    parser.add_argument("--has-roadmap", type=parse_bool, default=find_file(("ROADMAP.md", "docs/roadmap.md")))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    rules = load_rules()

    snapshot = build_snapshot(args, rules)
    previous = load_previous_snapshot()
    trend = compute_trend(snapshot, previous)
    markdown = render_markdown(snapshot, trend)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    audit_dir = ROOT / "docs" / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    snap_name = f"{stamp}_{snapshot['commit']}.json"
    snap_path = audit_dir / snap_name
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json_out:
        json_out_path = Path(args.json_out)
        json_out_path.parent.mkdir(parents=True, exist_ok=True)
        json_out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Reporte generado en: {out_path}")
    print(f"Snapshot guardado en: {snap_path}")


if __name__ == "__main__":
    main()
