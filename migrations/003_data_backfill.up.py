from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, column_type: str) -> None:
    if _column_exists(cursor, table, column):
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _ensure_legacy_compatibility_columns(cursor: sqlite3.Cursor) -> None:
    for column, column_type in [
        ("horas_mes_min", "INTEGER"),
        ("horas_ano_min", "INTEGER"),
        ("horas_jornada_defecto_min", "INTEGER"),
        ("is_active", "INTEGER DEFAULT 1"),
        ("cuadrante_uniforme", "INTEGER DEFAULT 0"),
        ("trabaja_finde", "INTEGER DEFAULT 0"),
        ("uuid", "TEXT"),
        ("updated_at", "TEXT"),
        ("source_device", "TEXT"),
        ("deleted", "INTEGER DEFAULT 0"),
    ]:
        _add_column_if_missing(cursor, "personas", column, column_type)

    for column, column_type in [
        ("desde_min", "INTEGER"),
        ("hasta_min", "INTEGER"),
        ("horas_solicitadas_min", "INTEGER"),
        ("notas", "TEXT"),
        ("generated", "INTEGER NOT NULL DEFAULT 1"),
        ("uuid", "TEXT"),
        ("updated_at", "TEXT"),
        ("source_device", "TEXT"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("created_at", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "solicitudes", column, column_type)


def _backfill_personas(cursor: sqlite3.Cursor) -> None:
    if _column_exists(cursor, "personas", "horas_mes"):
        cursor.execute(
            "UPDATE personas SET horas_mes_min = ROUND(horas_mes * 60) WHERE horas_mes_min IS NULL"
        )
    if _column_exists(cursor, "personas", "horas_ano"):
        cursor.execute(
            "UPDATE personas SET horas_ano_min = ROUND(horas_ano * 60) WHERE horas_ano_min IS NULL"
        )
    if _column_exists(cursor, "personas", "horas_jornada_defecto"):
        cursor.execute(
            """
            UPDATE personas
            SET horas_jornada_defecto_min = ROUND(horas_jornada_defecto * 60)
            WHERE horas_jornada_defecto_min IS NULL
            """
        )

    for day in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]:
        legacy = f"cuad_{day}"
        current = f"cuad_{day}_man_min"
        if _column_exists(cursor, "personas", legacy) and _column_exists(cursor, "personas", current):
            cursor.execute(
                f"UPDATE personas SET {current} = ROUND({legacy} * 60) WHERE {current} IS NULL"
            )

    cursor.execute(
        """
        UPDATE personas
        SET is_active = COALESCE(is_active, 1),
            cuadrante_uniforme = COALESCE(cuadrante_uniforme, 0),
            trabaja_finde = COALESCE(trabaja_finde, 0),
            deleted = COALESCE(deleted, 0)
        """
    )


def _backfill_solicitudes(cursor: sqlite3.Cursor) -> None:
    if _column_exists(cursor, "solicitudes", "horas"):
        cursor.execute(
            """
            UPDATE solicitudes
            SET horas_solicitadas_min = ROUND(horas * 60)
            WHERE horas_solicitadas_min IS NULL
            """
        )
    if _column_exists(cursor, "solicitudes", "desde"):
        cursor.execute(
            """
            UPDATE solicitudes
            SET desde_min = (
                CAST(substr(desde, 1, 2) AS INTEGER) * 60
                + CAST(substr(desde, 4, 2) AS INTEGER)
            )
            WHERE desde_min IS NULL AND desde IS NOT NULL
            """
        )
    if _column_exists(cursor, "solicitudes", "hasta"):
        cursor.execute(
            """
            UPDATE solicitudes
            SET hasta_min = (
                CAST(substr(hasta, 1, 2) AS INTEGER) * 60
                + CAST(substr(hasta, 4, 2) AS INTEGER)
            )
            WHERE hasta_min IS NULL AND hasta IS NOT NULL
            """
        )
    if _column_exists(cursor, "solicitudes", "observaciones"):
        cursor.execute(
            "UPDATE solicitudes SET notas = observaciones WHERE notas IS NULL AND observaciones IS NOT NULL"
        )

    cursor.execute(
        """
        UPDATE solicitudes
        SET generated = COALESCE(generated, 1),
            deleted = COALESCE(deleted, 0)
        """
    )


def _seed_sync_metadata(cursor: sqlite3.Cursor) -> None:
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cursor.execute("SELECT id, uuid, updated_at, deleted FROM personas")
    for row in cursor.fetchall():
        cursor.execute(
            """
            UPDATE personas
            SET uuid = ?, updated_at = COALESCE(updated_at, ?), deleted = COALESCE(deleted, 0)
            WHERE id = ?
            """,
            (row["uuid"] or str(uuid.uuid4()), now_iso, row["id"]),
        )

    cursor.execute("SELECT id, uuid, created_at, updated_at, fecha_solicitud, deleted FROM solicitudes")
    for row in cursor.fetchall():
        created_at = row["created_at"] or row["fecha_solicitud"] or now_iso
        cursor.execute(
            """
            UPDATE solicitudes
            SET uuid = ?,
                created_at = ?,
                updated_at = COALESCE(updated_at, ?),
                deleted = COALESCE(deleted, 0)
            WHERE id = ?
            """,
            (row["uuid"] or str(uuid.uuid4()), created_at, created_at, row["id"]),
        )


def run(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    _ensure_legacy_compatibility_columns(cursor)
    _backfill_personas(cursor)
    _backfill_solicitudes(cursor)
    _seed_sync_metadata(cursor)
