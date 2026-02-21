#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import logging
import platform
import subprocess
import sys
from dataclasses import dataclass

EXIT_OK = 0
EXIT_MISSING_DEPS = 2
EXIT_INTERNAL_ERROR = 3
MIN_PYTHON = (3, 10)


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    exit_code: int


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s event=%(event)s detail=%(detail)s",
    )


def _log(level: int, event: str, detail: str) -> None:
    logging.log(level, "preflight", extra={"event": event, "detail": detail})


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _pytest_cov_available() -> bool:
    if _has_module("pytest_cov"):
        return True

    cmd = [sys.executable, "-m", "pytest", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        _log(logging.ERROR, "pytest_help_failed", f"returncode={result.returncode}")
        return False
    return "--cov" in result.stdout


def run_preflight(require_radon: bool = False) -> PreflightResult:
    _log(logging.INFO, "python_version", platform.python_version())

    if sys.version_info < MIN_PYTHON:
        _log(
            logging.ERROR,
            "python_version_unsupported",
            f"requires>={MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        )
        return PreflightResult(ok=False, exit_code=EXIT_MISSING_DEPS)

    if not _has_module("pytest"):
        _log(logging.ERROR, "dependency_missing", "pytest")
        return PreflightResult(ok=False, exit_code=EXIT_MISSING_DEPS)

    if not _pytest_cov_available():
        _log(logging.ERROR, "dependency_missing", "pytest-cov")
        return PreflightResult(ok=False, exit_code=EXIT_MISSING_DEPS)

    if not _has_module("radon"):
        if require_radon:
            _log(logging.ERROR, "dependency_missing", "radon")
            return PreflightResult(ok=False, exit_code=EXIT_MISSING_DEPS)
        _log(logging.WARNING, "dependency_optional_missing", "radon")

    _log(logging.INFO, "preflight_ok", "all required checks passed")
    return PreflightResult(ok=True, exit_code=EXIT_OK)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight del entorno de tests.")
    parser.add_argument(
        "--require-radon",
        action="store_true",
        help="Marca radon como dependencia obligatoria.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    try:
        args = parse_args(argv)
        result = run_preflight(require_radon=args.require_radon)
        return result.exit_code
    except Exception as exc:  # pragma: no cover - ruta defensiva
        _log(logging.ERROR, "preflight_internal_error", repr(exc))
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
