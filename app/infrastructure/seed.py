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
            "Ana Pérez",
            "F",
            20.0,
            240.0,
            7.5,
            7.5,
            7.5,
            7.5,
            7.5,
            0.0,
            0.0,
            0.0,
        ),
        (
            "Carlos Ruiz",
            "M",
            18.0,
            216.0,
            8.0,
            8.0,
            8.0,
            8.0,
            8.0,
            0.0,
            0.0,
            0.0,
        ),
        (
            "Lucía Gómez",
            "F",
            22.0,
            264.0,
            6.5,
            6.5,
            6.5,
            6.5,
            6.5,
            0.0,
            0.0,
            0.0,
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO personas (
            nombre, genero, horas_mes, horas_ano, horas_jornada_defecto,
            cuad_lun, cuad_mar, cuad_mie, cuad_jue, cuad_vie, cuad_sab, cuad_dom
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        personas,
    )
    cursor.execute("SELECT id FROM personas ORDER BY id LIMIT 2")
    ids = [row[0] for row in cursor.fetchall()]
    solicitudes = [
        (
            ids[0],
            "2024-01-10",
            "2024-01-15",
            "09:00",
            "13:00",
            0,
            4.0,
            "Asamblea sindical",
            None,
            None,
        ),
        (
            ids[1],
            "2024-01-12",
            "2024-01-20",
            None,
            None,
            1,
            8.0,
            "Formación",
            None,
            None,
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO solicitudes (
            persona_id, fecha_solicitud, fecha_pedida, desde, hasta, completo,
            horas, observaciones, pdf_path, pdf_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        solicitudes,
    )
    connection.commit()
