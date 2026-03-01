from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from app.bootstrap.settings import resolve_log_dir
from app.infrastructure.local_config_store import LocalConfigStore


EXIT_OK = 0
EXIT_WARN = 1
EXIT_FAIL = 2


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str


def _check_logs_writable() -> CheckResult:
    try:
        log_dir = resolve_log_dir()
        probe = log_dir / ".doctor_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return CheckResult("logs_writable", "ok", f"Logs en '{log_dir}' con escritura.")
    except OSError as exc:
        return CheckResult("logs_writable", "fail", f"No se puede escribir en logs: {exc}")


def _check_sheets_config_present() -> CheckResult:
    config = LocalConfigStore().load()
    if config is None:
        return CheckResult("sheets_config", "warn", "Configuración de Sheets ausente.")

    credentials_present = bool(config.credentials_path and Path(config.credentials_path).exists())
    spreadsheet_present = bool(config.spreadsheet_id)

    if credentials_present and spreadsheet_present:
        return CheckResult("sheets_config", "ok", "Configuración de Sheets presente.")

    missing_parts: list[str] = []
    if not credentials_present:
        missing_parts.append("credenciales")
    if not spreadsheet_present:
        missing_parts.append("spreadsheet_id")
    return CheckResult(
        "sheets_config",
        "warn",
        f"Configuración de Sheets incompleta ({', '.join(missing_parts)}).",
    )


def _check_sqlite_available() -> CheckResult:
    try:
        with sqlite3.connect(":memory:") as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()
    except sqlite3.Error as exc:
        return CheckResult("sqlite", "fail", f"SQLite no disponible: {exc}")

    version_text = version[0] if version else "desconocida"
    return CheckResult("sqlite", "ok", f"SQLite disponible (versión {version_text}).")


def _resolve_exit_code(results: list[CheckResult]) -> int:
    if any(result.status == "fail" for result in results):
        return EXIT_FAIL
    if any(result.status == "warn" for result in results):
        return EXIT_WARN
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    _ = argv
    checks = [
        _check_logs_writable(),
        _check_sheets_config_present(),
        _check_sqlite_available(),
    ]
    exit_code = _resolve_exit_code(checks)
    payload = {
        "doctor": "horas_sindicales",
        "checks": [
            {"name": check.name, "status": check.status, "message": check.message}
            for check in checks
        ],
        "exit_code": exit_code,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
