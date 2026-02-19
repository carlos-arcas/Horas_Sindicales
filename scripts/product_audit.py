#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "auditoria_producto.md"


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


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "si", "sí"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Valor booleano inválido: {value!r}")


def git_short_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() or "N/D"
    except Exception:
        return "N/D"


def clamp_to_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def find_file(names: tuple[str, ...]) -> bool:
    return any((ROOT / name).exists() for name in names)


def detect_db_in_root() -> bool:
    patterns = ("*.db", "*.sqlite", "*.sqlite3")
    return any(ROOT.glob(pattern) for pattern in patterns)


def audit(args: argparse.Namespace) -> tuple[list[AreaResult], list[Improvement], float]:
    improvements: list[Improvement] = []

    # A) Arquitectura estructural
    architecture_penalty = args.critical_modules_over_500 * 5 + args.architecture_violations * 10
    if args.whitelist_active:
        architecture_penalty += 10
    architecture_score = clamp_to_score(100 - architecture_penalty)
    if args.critical_modules_over_500 > 0:
        area_gain = args.critical_modules_over_500 * 5
        improvements.append(
            Improvement(
                area="Arquitectura estructural",
                action=(
                    "Reducir módulos críticos (>500 líneas) "
                    f"de {args.critical_modules_over_500} a 0"
                ),
                area_gain=area_gain,
                weighted_gain=area_gain * 0.20,
            )
        )
    if args.architecture_violations > 0:
        area_gain = args.architecture_violations * 10
        improvements.append(
            Improvement(
                area="Arquitectura estructural",
                action=(
                    "Eliminar violaciones de capa "
                    f"(actuales: {args.architecture_violations})"
                ),
                area_gain=area_gain,
                weighted_gain=area_gain * 0.20,
            )
        )
    if args.whitelist_active:
        improvements.append(
            Improvement(
                area="Arquitectura estructural",
                action="Remover whitelist activa en tests de arquitectura",
                area_gain=10,
                weighted_gain=2.0,
            )
        )

    # B) Testing & cobertura
    testing_score = 0.0
    formula_b = []
    if args.coverage >= 60:
        testing_score += 50
        formula_b.append("50 base")
        growth = (args.coverage - 60) * 1.5
        testing_score += growth
        formula_b.append(f"+({args.coverage:.2f}-60)*1.5={growth:.2f}")
    if args.coverage < 65:
        testing_score -= 10
        formula_b.append("-10 por coverage < 65")
        improvements.append(
            Improvement(
                area="Testing & cobertura",
                action="Subir cobertura al menos a 65%",
                area_gain=10,
                weighted_gain=2.0,
            )
        )
    if args.tests_count > 100:
        testing_score += 5
        formula_b.append("+5 por tests_count > 100")
    else:
        improvements.append(
            Improvement(
                area="Testing & cobertura",
                action="Superar 100 tests automatizados",
                area_gain=5,
                weighted_gain=1.0,
            )
        )
    testing_score_clamped = clamp_to_score(testing_score)
    if testing_score_clamped < 100 and args.coverage < 93.34:
        potential = clamp_to_score((93.34 - args.coverage) * 1.5)
        if potential > 0:
            improvements.append(
                Improvement(
                    area="Testing & cobertura",
                    action="Incrementar cobertura para acercarse al score máximo del área",
                    area_gain=min(100 - testing_score_clamped, potential),
                    weighted_gain=min(100 - testing_score_clamped, potential) * 0.20,
                )
            )

    # C) Complejidad accidental
    complexity_penalty = round(args.max_file_lines / 100) + args.critical_modules_over_500 * 3
    complexity_score = clamp_to_score(100 - complexity_penalty)
    if args.max_file_lines > 0:
        area_gain = round(args.max_file_lines / 100)
        improvements.append(
            Improvement(
                area="Complejidad accidental",
                action=(
                    "Reducir tamaño del archivo más grande "
                    f"(actual: {args.max_file_lines} líneas)"
                ),
                area_gain=area_gain,
                weighted_gain=area_gain * 0.15,
            )
        )
    if args.critical_modules_over_500 > 0:
        area_gain = args.critical_modules_over_500 * 3
        improvements.append(
            Improvement(
                area="Complejidad accidental",
                action="Reducir cantidad de módulos >500 líneas",
                area_gain=area_gain,
                weighted_gain=area_gain * 0.15,
            )
        )

    # D) DevEx / CI / Governance
    devex_score = 0
    formula_d = []
    if args.ci_green:
        devex_score += 40
        formula_d.append("+40 CI en verde")
    else:
        improvements.append(
            Improvement("DevEx / CI / Governance", "Dejar CI en verde", 40, 6.0)
        )
    if args.release_automated:
        devex_score += 20
        formula_d.append("+20 release automatizado")
    else:
        improvements.append(
            Improvement("DevEx / CI / Governance", "Automatizar release", 20, 3.0)
        )
    if args.coverage_thresholds_aligned:
        devex_score += 10
        formula_d.append("+10 thresholds alineados")
    else:
        improvements.append(
            Improvement(
                "DevEx / CI / Governance",
                "Alinear coverage thresholds entre herramientas",
                10,
                1.5,
            )
        )
    devex_score = clamp_to_score(devex_score)

    # E) Observabilidad y resiliencia
    observability_score = 0
    formula_e = []
    if args.correlation_id_implemented:
        observability_score += 30
        formula_e.append("+30 correlation_id")
    else:
        improvements.append(
            Improvement(
                "Observabilidad y resiliencia",
                "Implementar correlation_id extremo a extremo",
                30,
                3.0,
            )
        )
    if args.structured_logs:
        observability_score += 20
        formula_e.append("+20 logs estructurados")
    else:
        improvements.append(
            Improvement(
                "Observabilidad y resiliencia",
                "Estandarizar logs estructurados",
                20,
                2.0,
            )
        )
    if args.main_window_lines > 500:
        observability_score -= 10
        formula_e.append("-10 por sync > 500 líneas")
        improvements.append(
            Improvement(
                "Observabilidad y resiliencia",
                "Reducir módulo sync principal por debajo de 500 líneas",
                10,
                1.0,
            )
        )
    observability_score = clamp_to_score(observability_score)

    # F) Configuración & seguridad
    security_score = 0
    formula_f = []
    if args.secrets_outside_repo:
        security_score += 50
        formula_f.append("+50 secretos fuera del repo")
    else:
        improvements.append(
            Improvement(
                "Configuración & seguridad",
                "Mover secretos fuera del repositorio",
                50,
                5.0,
            )
        )
    if args.db_in_repo_root:
        security_score -= 10
        formula_f.append("-10 DB en raíz")
        improvements.append(
            Improvement(
                "Configuración & seguridad",
                "Mover base de datos fuera de la raíz del repo",
                10,
                1.0,
            )
        )
    security_score = clamp_to_score(security_score)

    # G) Documentación & gobernanza
    doc_score = 0
    formula_g = []
    if args.has_contributing:
        doc_score += 40
        formula_g.append("+40 CONTRIBUTING")
    else:
        improvements.append(
            Improvement(
                "Documentación & gobernanza",
                "Agregar CONTRIBUTING con flujo de colaboración",
                40,
                4.0,
            )
        )
    if args.has_changelog:
        doc_score += 20
        formula_g.append("+20 CHANGELOG")
    else:
        improvements.append(
            Improvement(
                "Documentación & gobernanza",
                "Incorporar CHANGELOG versionado",
                20,
                2.0,
            )
        )
    if args.has_dod:
        doc_score += 20
        formula_g.append("+20 DoD formal")
    else:
        improvements.append(
            Improvement(
                "Documentación & gobernanza",
                "Formalizar Definition of Done",
                20,
                2.0,
            )
        )
    if args.has_roadmap:
        doc_score += 10
        formula_g.append("+10 roadmap")
    else:
        improvements.append(
            Improvement(
                "Documentación & gobernanza",
                "Definir roadmap técnico-producto",
                10,
                1.0,
            )
        )
    doc_score = clamp_to_score(doc_score)

    areas = [
        AreaResult(
            "Arquitectura estructural",
            20,
            architecture_score,
            f"100 - ({args.critical_modules_over_500}*5) - ({args.architecture_violations}*10)"
            + (" - 10 whitelist" if args.whitelist_active else ""),
        ),
        AreaResult("Testing & cobertura", 20, testing_score_clamped, " ; ".join(formula_b)),
        AreaResult(
            "Complejidad accidental",
            15,
            complexity_score,
            f"100 - round({args.max_file_lines}/100) - ({args.critical_modules_over_500}*3)",
        ),
        AreaResult("DevEx / CI / Governance", 15, devex_score, " ; ".join(formula_d)),
        AreaResult("Observabilidad y resiliencia", 10, observability_score, " ; ".join(formula_e)),
        AreaResult("Configuración & seguridad", 10, security_score, " ; ".join(formula_f)),
        AreaResult("Documentación & gobernanza", 10, doc_score, " ; ".join(formula_g)),
    ]

    weighted_global = sum(area.score * (area.weight / 100) for area in areas)
    return areas, improvements, weighted_global


def render_markdown(args: argparse.Namespace, areas: list[AreaResult], improvements: list[Improvement], weighted_global: float) -> str:
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit = git_short_commit()

    base_metrics = {
        "coverage": f"{args.coverage:.2f}",
        "max_file_lines": args.max_file_lines,
        "main_window_lines": args.main_window_lines,
        "use_cases_lines": args.use_cases_lines,
        "architecture_violations": args.architecture_violations,
        "ci_green": args.ci_green,
        "release_automated": args.release_automated,
        "whitelist_active": args.whitelist_active,
        "tests_count": args.tests_count,
        "critical_modules_over_500": args.critical_modules_over_500,
        "coverage_thresholds_aligned": args.coverage_thresholds_aligned,
        "correlation_id_implemented": args.correlation_id_implemented,
        "structured_logs": args.structured_logs,
        "secrets_outside_repo": args.secrets_outside_repo,
        "db_in_repo_root": args.db_in_repo_root,
        "has_contributing": args.has_contributing,
        "has_changelog": args.has_changelog,
        "has_dod": args.has_dod,
        "has_roadmap": args.has_roadmap,
    }

    sorted_improvements = sorted(
        improvements,
        key=lambda item: (item.weighted_gain, item.area_gain),
        reverse=True,
    )

    gaps = []
    for area in areas:
        if area.score < 100:
            gaps.append(f"- **{area.name}**: faltan {100 - area.score} puntos para llegar a 100.")
    if not gaps:
        gaps.append("- No hay brechas: todas las áreas están en 100.")

    top5 = sorted_improvements[:5]

    metrics_table = "\n".join(
        f"| `{name}` | `{value}` |" for name, value in base_metrics.items()
    )
    scores_table = "\n".join(
        (
            f"| {area.name} | {area.weight}% | {area.score} | "
            f"{area.score * (area.weight / 100):.2f} | {area.formula or 'N/A'} |"
        )
        for area in areas
    )
    plan_rows = "\n".join(
        f"{i}. **[{item.area}]** {item.action} (impacto área: +{item.area_gain}, impacto global: +{item.weighted_gain:.2f})."
        for i, item in enumerate(top5, start=1)
    )
    if not plan_rows:
        plan_rows = "1. No hay acciones pendientes; mantener la disciplina actual."

    return f"""# Auditoría técnica cuantitativa

- **Fecha:** {date_str}
- **Commit:** `{commit}`

## Métricas base

| Métrica | Valor |
|---|---|
{metrics_table}

## Score por áreas

| Área | Peso | Score (0-100) | Aporte ponderado | Cálculo |
|---|---:|---:|---:|---|
{scores_table}

## Score global ponderado

**{weighted_global:.2f} / 100**

## Brechas para llegar a 100

{chr(10).join(gaps)}

## Plan priorizado (Top 5)

{plan_rows}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auditor técnico cuantitativo de producto")
    parser.add_argument("--coverage", type=float, required=True)
    parser.add_argument("--max-file-lines", type=int, required=True)
    parser.add_argument("--main-window-lines", type=int, required=True)
    parser.add_argument("--use-cases-lines", type=int, required=True)
    parser.add_argument("--architecture-violations", type=int, required=True)
    parser.add_argument("--ci-green", type=parse_bool, required=True)
    parser.add_argument("--release-automated", type=parse_bool, required=True)
    parser.add_argument("--whitelist-active", type=parse_bool, required=True)
    parser.add_argument("--tests-count", type=int, required=True)
    parser.add_argument("--critical-modules-over-500", type=int, required=True)

    parser.add_argument("--coverage-thresholds-aligned", type=parse_bool, default=True)
    parser.add_argument("--correlation-id-implemented", type=parse_bool, default=True)
    parser.add_argument("--structured-logs", type=parse_bool, default=True)
    parser.add_argument("--secrets-outside-repo", type=parse_bool, default=True)
    parser.add_argument("--db-in-repo-root", type=parse_bool, default=detect_db_in_root())
    parser.add_argument(
        "--has-contributing",
        type=parse_bool,
        default=find_file(("CONTRIBUTING.md", "CONTRIBUTING")),
    )
    parser.add_argument(
        "--has-changelog",
        type=parse_bool,
        default=find_file(("CHANGELOG.md", "CHANGELOG")),
    )
    parser.add_argument(
        "--has-dod",
        type=parse_bool,
        default=(ROOT / "docs" / "definition_of_done.md").exists(),
    )
    parser.add_argument(
        "--has-roadmap",
        type=parse_bool,
        default=find_file(("ROADMAP.md", "docs/roadmap.md")),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    areas, improvements, weighted_global = audit(args)
    markdown = render_markdown(args, areas, improvements, weighted_global)

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(markdown, encoding="utf-8")
    print(f"Reporte generado en: {DOC_PATH}")


if __name__ == "__main__":
    main()
