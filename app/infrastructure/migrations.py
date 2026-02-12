from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Callable

MigrationHook = Callable[[sqlite3.Connection], None]


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


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestiona migraciones SQLite")
    parser.add_argument("command", choices=["up", "down", "status"], help="Operación a ejecutar")
    parser.add_argument("--db", default="horas_sindicales.db", help="Ruta al archivo SQLite")
    parser.add_argument("--steps", type=int, default=1, help="Número de migraciones a revertir")
    return parser


def main() -> int:
    parser = build_cli()
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row
    runner = MigrationRunner(connection)

    if args.command == "up":
        runner.apply_all()
    elif args.command == "down":
        runner.rollback(args.steps)
    else:
        for item in runner.status():
            marker = "[x]" if item["applied"] else "[ ]"
            print(f"{marker} {item['version']:04d} {item['name']}")

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
