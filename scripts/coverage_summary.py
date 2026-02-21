from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume cobertura desde coverage JSON")
    parser.add_argument("--repo", default=".", help="Ruta al repositorio")
    parser.add_argument("--package", default="app", help="Prefijo de paquete a analizar")
    parser.add_argument("--out-txt", required=True, help="Ruta de salida del resumen TXT")
    parser.add_argument("--out-json", default="", help="Ruta para coverage json (opcional)")
    parser.add_argument("--threshold", type=float, default=85.0, help="Umbral minimo de cobertura")
    parser.add_argument("--top", type=int, default=10, help="Cantidad de ficheros con peor cobertura")
    return parser.parse_args()


def _normalize(path: str) -> str:
    return path.replace('\\', '/')


def _in_package(file_path: str, package: str) -> bool:
    normalized = _normalize(file_path)
    package_prefix = package.strip('/').replace('\\', '/')
    return normalized.startswith(f"{package_prefix}/") or normalized == package_prefix


def _load_coverage_json(repo: Path, out_json: Path | None) -> dict[str, Any]:
    coverage_file = repo / ".coverage"
    selected_json = out_json or (repo / "coverage.json")

    if coverage_file.exists():
        selected_json.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-m", "coverage", "json", "-o", str(selected_json)]
        subprocess.run(cmd, cwd=repo, check=True)

    if not selected_json.exists():
        raise FileNotFoundError(
            f"No se encontro JSON de coverage en {selected_json}. Genera .coverage o indica --out-json existente."
        )

    return json.loads(selected_json.read_text(encoding="utf-8"))


def _build_summary(data: dict[str, Any], package: str, threshold: float, top_n: int) -> tuple[str, dict[str, Any]]:
    files = data.get("files", {})
    rows: list[dict[str, Any]] = []

    for file_path, payload in files.items():
        if package and not _in_package(file_path, package):
            continue
        summary = payload.get("summary", {})
        percent = float(summary.get("percent_covered", 0.0))
        rows.append(
            {
                "file": _normalize(file_path),
                "percent": percent,
                "covered_lines": int(summary.get("covered_lines", 0)),
                "num_statements": int(summary.get("num_statements", 0)),
                "missing_lines": int(summary.get("missing_lines", 0)),
            }
        )

    rows.sort(key=lambda item: (item["percent"], item["file"]))
    below = [item for item in rows if item["percent"] < threshold]
    worst = rows[: max(top_n, 0)]

    totals = data.get("totals", {})
    global_percent = float(totals.get("percent_covered", 0.0))

    lines = [
        "==== RESUMEN DE COBERTURA ====",
        f"Paquete objetivo: {package}",
        f"Umbral: {threshold:.2f}%",
        f"Cobertura global (coverage.py): {global_percent:.2f}%",
        f"Ficheros analizados: {len(rows)}",
        "",
        "-- TOP FICHEROS CON PEOR COBERTURA --",
    ]

    if worst:
        for idx, item in enumerate(worst, start=1):
            lines.append(
                f"{idx:02d}. {item['file']} -> {item['percent']:.2f}% "
                f"(cubiertas {item['covered_lines']}/{item['num_statements']}, faltan {item['missing_lines']})"
            )
    else:
        lines.append("(sin datos para el paquete indicado)")

    lines.extend(["", f"-- FICHEROS BAJO UMBRAL ({threshold:.2f}%) --"])
    if below:
        for item in below:
            lines.append(f"- {item['file']}: {item['percent']:.2f}%")
    else:
        lines.append("- Ninguno. Todos los ficheros cumplen el umbral.")

    summary_json = {
        "package": package,
        "threshold": threshold,
        "global_percent": global_percent,
        "analyzed_files": len(rows),
        "worst_files": worst,
        "below_threshold": below,
    }
    return "\n".join(lines) + "\n", summary_json


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    out_txt = Path(args.out_txt)
    out_json = Path(args.out_json) if args.out_json else None

    try:
        data = _load_coverage_json(repo=repo, out_json=out_json)
        summary_txt, _ = _build_summary(data, package=args.package, threshold=args.threshold, top_n=args.top)
    except Exception as exc:  # pragma: no cover - defensive path for batch integration
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(f"[ERROR] No se pudo generar resumen de cobertura: {exc}\n", encoding="utf-8")
        print(f"[ERROR] {exc}")
        return 1

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(summary_txt, encoding="utf-8")
    print(summary_txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
