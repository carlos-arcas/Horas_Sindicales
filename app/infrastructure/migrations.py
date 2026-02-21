from __future__ import annotations

import argparse
import hashlib
import importlib.util
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Callable

from app.bootstrap.logging import configure_logging
from app.bootstrap.settings import resolve_log_dir
from app.infrastructure.db import _default_db_path

MigrationHook = Callable[[sqlite3.Connection], None]


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationDefinition:
    version: int
    name: str
    up_sql: Path
    down_sql: Path
    up_hook: Path | None = None
    down_hook: Path | None = None


class MigrationRunner:
    def __init__(self, connection: sqlite3.Connection, migrations_dir: Path | None = None) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.migrations_dir = migrations_dir or Path(__file__).resolve().parents[2] / "migrations"
        self.migrations = self._discover_migrations()

    def apply_all(self) -> None:
        self._ensure_history_table()
        applied_versions = self._applied_versions()
        for migration in self.migrations:
            if migration.version in applied_versions:
                continue
            self._apply_migration(migration)

    def rollback(self, steps: int = 1) -> list[int]:
        self._ensure_history_table()
        cursor = self.connection.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT ?", (steps,))
        versions_to_rollback = [row["version"] for row in cursor.fetchall()]
        version_map = {migration.version: migration for migration in self.migrations}
        rolled_back: list[int] = []
        for version in versions_to_rollback:
            migration = version_map[version]
            self._rollback_migration(migration)
            rolled_back.append(version)
        return rolled_back

    def status(self) -> list[dict[str, object]]:
        self._ensure_history_table()
        applied_versions = self._applied_versions()
        return [
            {
                "version": migration.version,
                "name": migration.name,
                "applied": migration.version in applied_versions,
            }
            for migration in self.migrations
        ]

    def _ensure_history_table(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def _applied_versions(self) -> set[int]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT version FROM schema_migrations")
        return {row["version"] for row in cursor.fetchall()}

    def _apply_migration(self, migration: MigrationDefinition) -> None:
        sql_script = migration.up_sql.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql_script.encode("utf-8")).hexdigest()
        with self.connection:
            if sql_script.strip():
                self.connection.executescript(sql_script)
            if migration.up_hook is not None:
                hook = self._load_hook(migration.up_hook, "run")
                hook(self.connection)
            self.connection.execute(
                """
                INSERT INTO schema_migrations (version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    checksum,
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                ),
            )
            self.connection.execute(f"PRAGMA user_version = {migration.version}")

    def _rollback_migration(self, migration: MigrationDefinition) -> None:
        sql_script = migration.down_sql.read_text(encoding="utf-8")
        with self.connection:
            if migration.down_hook is not None:
                hook = self._load_hook(migration.down_hook, "run")
                hook(self.connection)
            if sql_script.strip():
                self.connection.executescript(sql_script)
            self.connection.execute("DELETE FROM schema_migrations WHERE version = ?", (migration.version,))
            previous = self.connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()["version"]
            self.connection.execute(f"PRAGMA user_version = {previous}")

    def _discover_migrations(self) -> list[MigrationDefinition]:
        definitions: list[MigrationDefinition] = []
        for up_file in sorted(self.migrations_dir.glob("*.up.sql")):
            stem = up_file.name[:-7]
            version_text, name = stem.split("_", maxsplit=1)
            version = int(version_text)
            down_file = self.migrations_dir / f"{stem}.down.sql"
            if not down_file.exists():
                raise FileNotFoundError(f"Missing down migration for {up_file.name}: {down_file}")
            up_hook = self.migrations_dir / f"{stem}.up.py"
            down_hook = self.migrations_dir / f"{stem}.down.py"
            definitions.append(
                MigrationDefinition(
                    version=version,
                    name=name,
                    up_sql=up_file,
                    down_sql=down_file,
                    up_hook=up_hook if up_hook.exists() else None,
                    down_hook=down_hook if down_hook.exists() else None,
                )
            )
        return definitions

    def _load_hook(self, file_path: Path, function_name: str) -> MigrationHook:
        spec = importlib.util.spec_from_file_location(f"migration_hook_{file_path.stem}", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import migration hook: {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not isinstance(module, ModuleType) or not hasattr(module, function_name):
            raise AttributeError(f"Hook {file_path} must define {function_name}(connection)")
        hook = getattr(module, function_name)
        return hook


def run_migrations(connection: sqlite3.Connection) -> None:
    MigrationRunner(connection).apply_all()
    run_data_fixups(connection)


def _normalize_legacy_date(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def run_data_fixups(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE solicitudes
        SET generated = 1
        WHERE uuid IS NOT NULL
          AND source_device IS NOT NULL
          AND (generated = 0 OR generated IS NULL)
          AND (deleted = 0 OR deleted IS NULL)
        """
    )

    cursor.execute(
        """
        SELECT id, fecha_pedida, fecha_solicitud
        FROM solicitudes
        WHERE (fecha_pedida LIKE '%/%' OR fecha_solicitud LIKE '%/%')
        """
    )
    rows = cursor.fetchall()
    updates: list[tuple[str | None, str | None, int]] = []
    for row in rows:
        fecha_pedida_iso = _normalize_legacy_date(row["fecha_pedida"])
        fecha_solicitud_iso = _normalize_legacy_date(row["fecha_solicitud"]) or fecha_pedida_iso
        if not fecha_pedida_iso:
            continue
        if fecha_pedida_iso == row["fecha_pedida"] and fecha_solicitud_iso == row["fecha_solicitud"]:
            continue
        updates.append((fecha_pedida_iso, fecha_solicitud_iso, row["id"]))

    if not updates:
        connection.commit()
        return

    cursor.executemany(
        """
        UPDATE solicitudes
        SET fecha_pedida = ?, fecha_solicitud = ?
        WHERE id = ?
        """,
        updates,
    )
    connection.commit()


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestiona migraciones SQLite")
    parser.add_argument("command", choices=["up", "down", "status"], help="Operación a ejecutar")
    parser.add_argument("--db", default=str(_default_db_path()), help="Ruta al archivo SQLite")
    parser.add_argument("--steps", type=int, default=1, help="Número de migraciones a revertir")
    return parser


def main() -> int:
    configure_logging(resolve_log_dir())
    parser = build_cli()
    args = parser.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    runner = MigrationRunner(connection)

    if args.command == "up":
        runner.apply_all()
        logger.info("Migraciones aplicadas", extra={"context_module": __name__, "context_function": "main", "command": "up"})
    elif args.command == "down":
        rolled_back = runner.rollback(args.steps)
        logger.info(
            "Migraciones revertidas",
            extra={"context_module": __name__, "context_function": "main", "command": "down", "count": len(rolled_back)},
        )
    else:
        for item in runner.status():
            marker = "[x]" if item["applied"] else "[ ]"
            logger.info(
                "Estado de migración %s %04d %s",
                marker,
                item["version"],
                item["name"],
                extra={"context_module": __name__, "context_function": "main", "command": "status"},
            )

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
