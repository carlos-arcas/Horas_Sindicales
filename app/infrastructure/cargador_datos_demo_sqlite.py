from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2

from app.application.ports.datos_demo_puerto import CargadorDatosDemoPuerto, ResultadoCargaDemoPuerto
from app.infrastructure.db import get_connection
from app.infrastructure.migrations import run_migrations

logger = logging.getLogger(__name__)


class CargadorDatosDemoSQLite(CargadorDatosDemoPuerto):
    def __init__(self, proveedor_dataset, db_path: Path) -> None:
        self._proveedor_dataset = proveedor_dataset
        self._db_path = db_path

    def cargar(self, modo: str) -> ResultadoCargaDemoPuerto:
        try:
            dataset = self._proveedor_dataset.cargar()
            self._asegurar_directorio(self._db_path.parent)
            if modo.upper() == "BACKUP":
                backup_path = self._crear_backup()
                warnings = (f"Backup creado: {backup_path.name}",)
            else:
                warnings = ()
            self._recrear_base(dataset)
            return ResultadoCargaDemoPuerto(
                ok=True,
                mensaje_usuario="Demo cargada",
                warnings=warnings,
                acciones_sugeridas=("IR_SOLICITUDES",),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("carga_demo_fallida")
            return ResultadoCargaDemoPuerto(
                ok=False,
                mensaje_usuario="No se pudieron cargar los datos de demostración.",
                detalles=str(exc),
                acciones_sugeridas=("VER_DETALLES",),
            )

    def _asegurar_directorio(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def _crear_backup(self) -> Path:
        if not self._db_path.exists():
            return self._db_path.with_name("horas_sindicales_pre_demo.sqlite")
        backup_path = self._db_path.with_name("horas_sindicales_pre_demo.sqlite")
        copy2(self._db_path, backup_path)
        return backup_path

    def _recrear_base(self, dataset: dict[str, object]) -> None:
        if self._db_path.exists():
            self._db_path.unlink()
        connection = get_connection(self._db_path)
        try:
            run_migrations(connection)
            self._insertar_dataset(connection, dataset)
            connection.commit()
        finally:
            connection.close()

    def _insertar_dataset(self, connection: sqlite3.Connection, dataset: dict[str, object]) -> None:
        cursor = connection.cursor()
        delegadas = dataset.get("delegadas", [])
        for delegada in delegadas:
            self._insertar_delegada(cursor, delegada)
        solicitudes = dataset.get("solicitudes", [])
        for solicitud in solicitudes:
            self._insertar_solicitud(cursor, solicitud)

    def _insertar_delegada(self, cursor: sqlite3.Cursor, delegada: dict[str, object]) -> None:
        now = datetime.now(UTC).isoformat()
        params = (
            delegada["nombre"],
            delegada.get("genero", "F"),
            int(delegada.get("horas_mes_min", 720)),
            int(delegada.get("horas_ano_min", 8640)),
            now,
        )
        cursor.execute(
            """
            INSERT INTO personas (
                nombre, genero, horas_mes_min, horas_ano_min, is_active,
                cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min, cuadrante_uniforme, trabaja_finde,
                updated_at, deleted
            ) VALUES (?, ?, ?, ?, 1, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 0, 0, 0, 0, 1, 0, ?, 0)
            """,
            params,
        )

    def _insertar_solicitud(self, cursor: sqlite3.Cursor, solicitud: dict[str, object]) -> None:
        persona_id = self._resolver_persona_id(cursor, str(solicitud["delegada"]))
        now = datetime.now(UTC).isoformat()
        fecha = str(solicitud["fecha_pedida"])
        params = (
            persona_id,
            fecha,
            fecha,
            solicitud.get("desde_min"),
            solicitud.get("hasta_min"),
            1 if solicitud.get("completo", False) else 0,
            int(solicitud.get("horas_solicitadas_min", 0)),
            str(solicitud.get("notas", "")),
            str(solicitud.get("notas", "")),
            1 if solicitud.get("generated", False) else 0,
            now,
            now,
        )
        cursor.execute(
            """
            INSERT INTO solicitudes (
                persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min,
                completo, horas_solicitadas_min, observaciones, notas,
                generated, updated_at, created_at, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            params,
        )

    def _resolver_persona_id(self, cursor: sqlite3.Cursor, nombre: str) -> int:
        row = cursor.execute("SELECT id FROM personas WHERE nombre = ?", (nombre,)).fetchone()
        if row is None:
            raise ValueError(f"Delegada no encontrada en dataset demo: {nombre}")
        return int(row[0])
