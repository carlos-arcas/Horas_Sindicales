from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run_migrations(connection: sqlite3.Connection) -> None:
    logger.info("Ejecutando migraciones")
    cursor = connection.cursor()
    _ensure_grupo_config(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            genero TEXT NOT NULL CHECK(genero IN ('M','F')),
            horas_mes_min INTEGER,
            horas_ano_min INTEGER,
            horas_jornada_defecto_min INTEGER,
            is_active INTEGER DEFAULT 1,
            cuad_lun_man_min INTEGER,
            cuad_lun_tar_min INTEGER,
            cuad_mar_man_min INTEGER,
            cuad_mar_tar_min INTEGER,
            cuad_mie_man_min INTEGER,
            cuad_mie_tar_min INTEGER,
            cuad_jue_man_min INTEGER,
            cuad_jue_tar_min INTEGER,
            cuad_vie_man_min INTEGER,
            cuad_vie_tar_min INTEGER,
            cuad_sab_man_min INTEGER,
            cuad_sab_tar_min INTEGER,
            cuad_dom_man_min INTEGER,
            cuad_dom_tar_min INTEGER,
            cuadrante_uniforme INTEGER DEFAULT 0,
            trabaja_finde INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_id INTEGER NOT NULL,
            fecha_solicitud TEXT NOT NULL,
            fecha_pedida TEXT NOT NULL,
            desde_min INTEGER NULL,
            hasta_min INTEGER NULL,
            completo INTEGER NOT NULL,
            horas_solicitadas_min INTEGER,
            observaciones TEXT NULL,
            notas TEXT NULL,
            pdf_path TEXT NULL,
            pdf_hash TEXT NULL,
            generated INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sol_persona_fecha_pedida
        ON solicitudes (persona_id, fecha_pedida)
        """
    )
    connection.commit()
    _ensure_personas_columns(cursor)
    _ensure_solicitudes_columns(cursor)
    _ensure_sync_tables(cursor)
    _ensure_sync_columns(cursor)
    _seed_sync_metadata(cursor)
    connection.commit()


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _execute_with_validation(cursor: sqlite3.Cursor, sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, params)


def _add_column_if_missing(
    cursor: sqlite3.Cursor, table: str, column: str, column_type: str
) -> None:
    if _column_exists(cursor, table, column):
        return
    sanitized_type = column_type.replace("UNIQUE", "").replace("unique", "")
    sanitized_type = " ".join(sanitized_type.split())
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sanitized_type}")


def _ensure_unique_uuids(cursor: sqlite3.Cursor, table: str) -> None:
    cursor.execute(f"SELECT id, uuid FROM {table} WHERE uuid IS NULL")
    for row in cursor.fetchall():
        cursor.execute(
            f"UPDATE {table} SET uuid = ? WHERE id = ?",
            (str(uuid.uuid4()), row["id"]),
        )

    cursor.execute(
        f"""
        SELECT uuid
        FROM {table}
        WHERE uuid IS NOT NULL
        GROUP BY uuid
        HAVING COUNT(*) > 1
        """
    )
    for row in cursor.fetchall():
        cursor.execute(
            f"SELECT id FROM {table} WHERE uuid = ? ORDER BY id", (row["uuid"],)
        )
        ids = [duplicate["id"] for duplicate in cursor.fetchall()]
        for duplicate_id in ids[1:]:
            cursor.execute(
                f"UPDATE {table} SET uuid = ? WHERE id = ?",
                (str(uuid.uuid4()), duplicate_id),
            )


def _ensure_personas_columns(cursor: sqlite3.Cursor) -> None:
    for column, column_type in [
        ("horas_mes_min", "INTEGER"),
        ("horas_ano_min", "INTEGER"),
        ("horas_jornada_defecto_min", "INTEGER"),
        ("is_active", "INTEGER DEFAULT 1"),
        ("cuad_lun_man_min", "INTEGER"),
        ("cuad_lun_tar_min", "INTEGER"),
        ("cuad_mar_man_min", "INTEGER"),
        ("cuad_mar_tar_min", "INTEGER"),
        ("cuad_mie_man_min", "INTEGER"),
        ("cuad_mie_tar_min", "INTEGER"),
        ("cuad_jue_man_min", "INTEGER"),
        ("cuad_jue_tar_min", "INTEGER"),
        ("cuad_vie_man_min", "INTEGER"),
        ("cuad_vie_tar_min", "INTEGER"),
        ("cuad_sab_man_min", "INTEGER"),
        ("cuad_sab_tar_min", "INTEGER"),
        ("cuad_dom_man_min", "INTEGER"),
        ("cuad_dom_tar_min", "INTEGER"),
        ("cuadrante_uniforme", "INTEGER DEFAULT 0"),
        ("trabaja_finde", "INTEGER DEFAULT 0"),
    ]:
        _add_column_if_missing(cursor, "personas", column, column_type)

    if _column_exists(cursor, "personas", "horas_mes"):
        cursor.execute(
            """
            UPDATE personas
            SET horas_mes_min = ROUND(horas_mes * 60)
            WHERE horas_mes_min IS NULL
            """
        )
    if _column_exists(cursor, "personas", "horas_ano"):
        cursor.execute(
            """
            UPDATE personas
            SET horas_ano_min = ROUND(horas_ano * 60)
            WHERE horas_ano_min IS NULL
            """
        )
    if _column_exists(cursor, "personas", "horas_jornada_defecto"):
        cursor.execute(
            """
            UPDATE personas
            SET horas_jornada_defecto_min = ROUND(horas_jornada_defecto * 60)
            WHERE horas_jornada_defecto_min IS NULL
            """
        )

    if _column_exists(cursor, "personas", "is_active"):
        cursor.execute(
            """
            UPDATE personas
            SET is_active = 1
            WHERE is_active IS NULL
            """
        )


    if _column_exists(cursor, "personas", "cuadrante_uniforme"):
        cursor.execute(
            """
            UPDATE personas
            SET cuadrante_uniforme = 0
            WHERE cuadrante_uniforme IS NULL
            """
        )

    if _column_exists(cursor, "personas", "trabaja_finde"):
        cursor.execute(
            """
            UPDATE personas
            SET trabaja_finde = 0
            WHERE trabaja_finde IS NULL
            """
        )

    for dia in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]:
        col = f"cuad_{dia}"
        man_col = f"cuad_{dia}_man_min"
        if _column_exists(cursor, "personas", col):
            cursor.execute(
                f"""
                UPDATE personas
                SET {man_col} = ROUND({col} * 60)
                WHERE {man_col} IS NULL
                """
            )


def _ensure_solicitudes_columns(cursor: sqlite3.Cursor) -> None:
    for column, column_type in [
        ("desde_min", "INTEGER"),
        ("hasta_min", "INTEGER"),
        ("horas_solicitadas_min", "INTEGER"),
        ("notas", "TEXT NULL"),
        ("generated", "INTEGER NOT NULL DEFAULT 1"),
    ]:
        _add_column_if_missing(cursor, "solicitudes", column, column_type)

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
            """
            UPDATE solicitudes
            SET notas = observaciones
            WHERE notas IS NULL AND observaciones IS NOT NULL
            """
        )

    if _column_exists(cursor, "solicitudes", "generated"):
        cursor.execute(
            """
            UPDATE solicitudes
            SET generated = 1
            WHERE generated IS NULL
            """
        )


def _ensure_sync_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            last_sync_at TEXT NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO sync_state (id, last_sync_at)
        VALUES (1, NULL)
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            local_snapshot_json TEXT NOT NULL,
            remote_snapshot_json TEXT NOT NULL,
            detected_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cuadrantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE,
            delegada_uuid TEXT NOT NULL,
            dia_semana TEXT NOT NULL,
            man_min INTEGER,
            tar_min INTEGER,
            updated_at TEXT,
            source_device TEXT,
            deleted INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pdf_log (
            pdf_id TEXT PRIMARY KEY,
            delegada_uuid TEXT,
            rango_fechas TEXT,
            fecha_generacion TEXT,
            hash TEXT,
            updated_at TEXT,
            source_device TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT,
            source_device TEXT
        )
        """
    )


def _ensure_sync_columns(cursor: sqlite3.Cursor) -> None:
    for column, column_type in [
        ("uuid", "TEXT"),
        ("updated_at", "TEXT"),
        ("source_device", "TEXT"),
        ("deleted", "INTEGER DEFAULT 0"),
    ]:
        _add_column_if_missing(cursor, "personas", column, column_type)
    _ensure_unique_uuids(cursor, "personas")
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_personas_uuid
        ON personas(uuid)
        """
    )
    for column, column_type in [
        ("uuid", "TEXT"),
        ("updated_at", "TEXT"),
        ("source_device", "TEXT"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("created_at", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "solicitudes", column, column_type)
    _ensure_unique_uuids(cursor, "solicitudes")
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_solicitudes_uuid
        ON solicitudes(uuid)
        """
    )


def _seed_sync_metadata(cursor: sqlite3.Cursor) -> None:
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cursor.execute("SELECT id, uuid, updated_at, deleted FROM personas")
    for row in cursor.fetchall():
        persona_uuid = row["uuid"] or str(uuid.uuid4())
        updated_at = row["updated_at"] or now_iso
        deleted = row["deleted"] if row["deleted"] is not None else 0
        _execute_with_validation(
            cursor,
            """
            UPDATE personas
            SET uuid = ?, updated_at = ?, deleted = ?
            WHERE id = ?
            """,
            (persona_uuid, updated_at, deleted, row["id"]),
            "personas.seed_sync_metadata",
        )
    cursor.execute("SELECT id, uuid, updated_at, deleted, created_at, fecha_solicitud FROM solicitudes")
    for row in cursor.fetchall():
        solicitud_uuid = row["uuid"] or str(uuid.uuid4())
        created_at = row["created_at"] or row["fecha_solicitud"] or now_iso
        updated_at = row["updated_at"] or created_at or now_iso
        deleted = row["deleted"] if row["deleted"] is not None else 0
        _execute_with_validation(
            cursor,
            """
            UPDATE solicitudes
            SET uuid = ?, created_at = ?, updated_at = ?, deleted = ?
            WHERE id = ?
            """,
            (solicitud_uuid, created_at, updated_at, deleted, row["id"]),
            "solicitudes.seed_sync_metadata",
        )

def _ensure_grupo_config(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS grupo_config (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            nombre_grupo TEXT NULL,
            bolsa_anual_grupo_min INTEGER DEFAULT 0,
            pdf_logo_path TEXT DEFAULT 'logo.png',
            pdf_intro_text TEXT DEFAULT 'Conforme a lo dispuesto en el art.68 e) del Estatuto de los Trabajadores, aprobado por el Real Decreto Legislativo 1/1995 de 24 de marzo, dispense la ausencia al trabajo de los/as trabajadores/as que a continuación se relacionan, los cuales han de resolver asuntos relativos al ejercicio de sus funciones, representando al personal de su empresa.',
            pdf_include_hours_in_horario INTEGER NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO grupo_config (
            id, nombre_grupo, bolsa_anual_grupo_min, pdf_logo_path, pdf_intro_text, pdf_include_hours_in_horario
        ) VALUES (
            1, NULL, 0, 'logo.png',
            'Conforme a lo dispuesto en el art.68 e) del Estatuto de los Trabajadores, aprobado por el Real Decreto Legislativo 1/1995 de 24 de marzo, dispense la ausencia al trabajo de los/as trabajadores/as que a continuación se relacionan, los cuales han de resolver asuntos relativos al ejercicio de sus funciones, representando al personal de su empresa.',
            NULL
        )
        """
    )
