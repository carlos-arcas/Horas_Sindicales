from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def run_migrations(connection: sqlite3.Connection) -> None:
    logger.info("Ejecutando migraciones")
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            genero TEXT NOT NULL CHECK(genero IN ('M','F')),
            horas_mes_min INTEGER,
            horas_ano_min INTEGER,
            horas_jornada_defecto_min INTEGER,
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
            cuad_dom_tar_min INTEGER
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
            pdf_path TEXT NULL,
            pdf_hash TEXT NULL,
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
    connection.commit()


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _add_column_if_missing(
    cursor: sqlite3.Cursor, table: str, column: str, column_type: str
) -> None:
    if _column_exists(cursor, table, column):
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _ensure_personas_columns(cursor: sqlite3.Cursor) -> None:
    for column, column_type in [
        ("horas_mes_min", "INTEGER"),
        ("horas_ano_min", "INTEGER"),
        ("horas_jornada_defecto_min", "INTEGER"),
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
