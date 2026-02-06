from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _validate_params_length(sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )


def _validate_executemany(sql: str, params_list: list[tuple[object, ...]], context: str) -> None:
    for index, params in enumerate(params_list):
        _validate_params_length(sql, params, f"{context}[{index}]")


def seed_if_empty(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM personas")
    count = cursor.fetchone()[0]
    if count:
        return
    logger.info("Insertando datos de ejemplo")
    personas = [
        (
            "Lorena Aznar Ramos",
            "F",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        (
            "Dora Inés Solano Franco",
            "F",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
    ]
    has_uuid = _column_exists(cursor, "personas", "uuid")
    has_updated_at = _column_exists(cursor, "personas", "updated_at")
    has_deleted = _column_exists(cursor, "personas", "deleted")
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extra_columns: list[str] = []
    if has_uuid:
        extra_columns.append("uuid")
    if has_updated_at:
        extra_columns.append("updated_at")
    if has_deleted:
        extra_columns.append("deleted")

    def _extra_values() -> tuple[object, ...]:
        values: list[object] = []
        if has_uuid:
            values.append(str(uuid.uuid4()))
        if has_updated_at:
            values.append(now_iso)
        if has_deleted:
            values.append(0)
        return tuple(values)

    if _column_exists(cursor, "personas", "horas_mes"):
        base_columns = [
            "nombre",
            "genero",
            "horas_mes",
            "horas_ano",
            "horas_jornada_defecto",
            "cuad_lun",
            "cuad_mar",
            "cuad_mie",
            "cuad_jue",
            "cuad_vie",
            "cuad_sab",
            "cuad_dom",
            "horas_mes_min",
            "horas_ano_min",
            "horas_jornada_defecto_min",
            "cuad_lun_man_min",
            "cuad_lun_tar_min",
            "cuad_mar_man_min",
            "cuad_mar_tar_min",
            "cuad_mie_man_min",
            "cuad_mie_tar_min",
            "cuad_jue_man_min",
            "cuad_jue_tar_min",
            "cuad_vie_man_min",
            "cuad_vie_tar_min",
            "cuad_sab_man_min",
            "cuad_sab_tar_min",
            "cuad_dom_man_min",
            "cuad_dom_tar_min",
        ]
        columns = base_columns + extra_columns
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO personas ({', '.join(columns)}) VALUES ({placeholders})"
        params_list = [
            (
                persona[0],
                persona[1],
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                *persona[2:],
                *_extra_values(),
            )
            for persona in personas
        ]
        _validate_executemany(sql, params_list, "personas.seed_with_legacy_columns")
        cursor.executemany(sql, params_list)
    else:
        base_columns = [
            "nombre",
            "genero",
            "horas_mes_min",
            "horas_ano_min",
            "horas_jornada_defecto_min",
            "cuad_lun_man_min",
            "cuad_lun_tar_min",
            "cuad_mar_man_min",
            "cuad_mar_tar_min",
            "cuad_mie_man_min",
            "cuad_mie_tar_min",
            "cuad_jue_man_min",
            "cuad_jue_tar_min",
            "cuad_vie_man_min",
            "cuad_vie_tar_min",
            "cuad_sab_man_min",
            "cuad_sab_tar_min",
            "cuad_dom_man_min",
            "cuad_dom_tar_min",
        ]
        columns = base_columns + extra_columns
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO personas ({', '.join(columns)}) VALUES ({placeholders})"
        params_list = [(*persona, *_extra_values()) for persona in personas]
        _validate_executemany(sql, params_list, "personas.seed_min_columns")
        cursor.executemany(sql, params_list)
    connection.commit()


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())
