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
            horas_mes REAL NOT NULL,
            horas_ano REAL NOT NULL,
            horas_jornada_defecto REAL NOT NULL,
            cuad_lun REAL,
            cuad_mar REAL,
            cuad_mie REAL,
            cuad_jue REAL,
            cuad_vie REAL,
            cuad_sab REAL,
            cuad_dom REAL
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
            desde TEXT NULL,
            hasta TEXT NULL,
            completo INTEGER NOT NULL,
            horas REAL NOT NULL,
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
