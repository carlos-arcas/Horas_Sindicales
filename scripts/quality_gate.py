#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".config" / "quality_gate.json"


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_coverage_threshold(config: dict[str, object]) -> int:
    threshold = config.get("coverage_fail_under_core", config.get("coverage_fail_under"))
    if not isinstance(threshold, int):
        raise SystemExit(
            f"Invalid coverage threshold in {CONFIG_PATH}. "
            "Expected integer in 'coverage_fail_under_core' or 'coverage_fail_under'."
        )
    return threshold


def load_core_coverage_targets(config: dict[str, object]) -> list[str]:
    raw_targets = config.get("core_coverage_targets")
    if raw_targets is None:
        return ["app"]
    if not isinstance(raw_targets, list) or not all(
        isinstance(item, str) for item in raw_targets
    ):
        raise SystemExit(
            f"Invalid 'core_coverage_targets' in {CONFIG_PATH}. Expected list[str]."
        )
    return raw_targets


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    config = load_config()
    threshold = load_coverage_threshold(config)
    coverage_targets = load_core_coverage_targets(config)

    print(f"Using CORE coverage threshold: {threshold}%")
    print(f"CORE coverage targets: {', '.join(coverage_targets)}")

    run(["ruff", "check", "."])

    pytest_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "not ui",
        "--cov-report=term-missing",
        f"--cov-fail-under={threshold}",
    ]
    for target in coverage_targets:
        pytest_command.append(f"--cov={target}")

    run(pytest_command)
    run([sys.executable, "scripts/report_quality.py", "--out", "logs/quality_report.txt"])


if __name__ == "__main__":
    main()
