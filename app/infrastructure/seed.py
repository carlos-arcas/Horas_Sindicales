from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


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
    if _column_exists(cursor, "personas", "horas_mes"):
        cursor.executemany(
            """
            INSERT INTO personas (
                nombre, genero,
                horas_mes, horas_ano, horas_jornada_defecto,
                cuad_lun, cuad_mar, cuad_mie, cuad_jue, cuad_vie, cuad_sab, cuad_dom,
                horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
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
                )
                for persona in personas
            ],
        )
    else:
        cursor.executemany(
            """
            INSERT INTO personas (
                nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            personas,
        )
    connection.commit()


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())
