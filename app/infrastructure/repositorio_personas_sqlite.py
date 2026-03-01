from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Iterable, TypeVar

from app.domain.models import Persona
from app.domain.ports import PersonaRepository
from app.infrastructure.repos_sqlite_builders import (
    PERSONA_SELECT_FIELDS,
    persona_insert_params,
    persona_update_params,
    row_to_persona,
)
from app.infrastructure.configuracion_conexion_sqlite import configurar_conexion
from app.infrastructure.sqlite_uow import transaccion


logger = logging.getLogger(__name__)

_LOCKED_RETRY_BACKOFF_SECONDS = (0.05, 0.15, 0.3)
_T = TypeVar("_T")


def _configure_connection_for_runtime(connection: sqlite3.Connection) -> None:
    """Aplica pragmas defensivos para minimizar conflictos de lock en runtime."""
    try:
        configurar_conexion(connection, busy_timeout_ms=30000)
        connection.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        logger.debug("sqlite_runtime_pragmas_skipped", exc_info=True)


def _is_locked_operational_error(error: sqlite3.OperationalError) -> bool:
    return "locked" in str(error).lower()


def _run_with_locked_retry(operation: Callable[[], _T], *, context: str) -> _T:
    for attempt, delay_seconds in enumerate(_LOCKED_RETRY_BACKOFF_SECONDS, start=1):
        try:
            return operation()
        except sqlite3.OperationalError as error:
            if not _is_locked_operational_error(error):
                raise
            logger.warning(
                "SQLite locked in %s (attempt=%s/%s); retrying in %.0fms",
                context,
                attempt,
                len(_LOCKED_RETRY_BACKOFF_SECONDS),
                delay_seconds * 1000,
            )
            time.sleep(delay_seconds)

    return operation()


def _run_in_transaction_with_retry(
    connection: sqlite3.Connection,
    operation: Callable[[], _T],
    *,
    context: str,
) -> _T:
    def _operation_in_transaction() -> _T:
        with transaccion(connection):
            return operation()

    return _run_with_locked_retry(_operation_in_transaction, context=context)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _execute_with_validation(cursor: sqlite3.Cursor, sql: str, params: Iterable[object], context: str) -> None:
    expected = sql.count("?")
    params_list = list(params)
    actual = len(params_list)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, tuple(params_list))


class RepositorioPersonasSQLite(PersonaRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        _configure_connection_for_runtime(self._connection)

    def list_all(self, include_inactive: bool = False) -> Iterable[Persona]:
        cursor = self._connection.cursor()
        sql = f"SELECT {PERSONA_SELECT_FIELDS} FROM personas"
        if not include_inactive:
            sql += " WHERE is_active = 1 AND (deleted = 0 OR deleted IS NULL)"
        else:
            sql += " WHERE deleted = 0 OR deleted IS NULL"
        sql += " ORDER BY nombre"
        cursor.execute(sql)
        return [row_to_persona(row) for row in cursor.fetchall()]

    def get_by_id(self, persona_id: int) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            f"SELECT {PERSONA_SELECT_FIELDS} FROM personas WHERE id = ? AND (deleted = 0 OR deleted IS NULL)",
            (persona_id,),
        )
        row = cursor.fetchone()
        return row_to_persona(row) if row else None

    def get_by_nombre(self, nombre: str) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            f"SELECT {PERSONA_SELECT_FIELDS} FROM personas WHERE nombre = ? AND (deleted = 0 OR deleted IS NULL)",
            (nombre,),
        )
        row = cursor.fetchone()
        return row_to_persona(row) if row else None

    def create(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        persona_uuid = str(uuid.uuid4())
        updated_at = _now_iso()

        def _operation() -> None:
            _execute_with_validation(
                cursor,
                """
                INSERT INTO personas (
                    uuid, nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min, is_active,
                    cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                    cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                    cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                    cuad_dom_man_min, cuad_dom_tar_min, cuadrante_uniforme, trabaja_finde,
                    updated_at, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                persona_insert_params(persona, persona_uuid, updated_at),
                "personas.insert",
            )

        _run_in_transaction_with_retry(self._connection, _operation, context="personas.create")
        return Persona(
            id=cursor.lastrowid,
            nombre=persona.nombre,
            genero=persona.genero,
            horas_mes_min=persona.horas_mes_min,
            horas_ano_min=persona.horas_ano_min,
            is_active=persona.is_active,
            cuad_lun_man_min=persona.cuad_lun_man_min,
            cuad_lun_tar_min=persona.cuad_lun_tar_min,
            cuad_mar_man_min=persona.cuad_mar_man_min,
            cuad_mar_tar_min=persona.cuad_mar_tar_min,
            cuad_mie_man_min=persona.cuad_mie_man_min,
            cuad_mie_tar_min=persona.cuad_mie_tar_min,
            cuad_jue_man_min=persona.cuad_jue_man_min,
            cuad_jue_tar_min=persona.cuad_jue_tar_min,
            cuad_vie_man_min=persona.cuad_vie_man_min,
            cuad_vie_tar_min=persona.cuad_vie_tar_min,
            cuad_sab_man_min=persona.cuad_sab_man_min,
            cuad_sab_tar_min=persona.cuad_sab_tar_min,
            cuad_dom_man_min=persona.cuad_dom_man_min,
            cuad_dom_tar_min=persona.cuad_dom_tar_min,
            cuadrante_uniforme=persona.cuadrante_uniforme,
            trabaja_finde=persona.trabaja_finde,
        )

    def update(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        updated_at = _now_iso()

        def _operation() -> None:
            _execute_with_validation(
                cursor,
                """
                UPDATE personas
                SET nombre = ?, genero = ?, horas_mes_min = ?, horas_ano_min = ?, horas_jornada_defecto_min = ?,
                    is_active = ?,
                    cuad_lun_man_min = ?, cuad_lun_tar_min = ?, cuad_mar_man_min = ?, cuad_mar_tar_min = ?,
                    cuad_mie_man_min = ?, cuad_mie_tar_min = ?, cuad_jue_man_min = ?, cuad_jue_tar_min = ?,
                    cuad_vie_man_min = ?, cuad_vie_tar_min = ?, cuad_sab_man_min = ?, cuad_sab_tar_min = ?,
                    cuad_dom_man_min = ?, cuad_dom_tar_min = ?, cuadrante_uniforme = ?, trabaja_finde = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                persona_update_params(persona, updated_at),
                "personas.update",
            )

        _run_in_transaction_with_retry(self._connection, _operation, context="personas.update")
        return persona

    def get_by_uuid(self, persona_uuid: str) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            f"SELECT {PERSONA_SELECT_FIELDS} FROM personas WHERE uuid = ? AND (deleted = 0 OR deleted IS NULL)",
            (persona_uuid,),
        )
        row = cursor.fetchone()
        return row_to_persona(row) if row else None

    def get_or_create_uuid(self, persona_id: int) -> str | None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT uuid FROM personas WHERE id = ? AND (deleted = 0 OR deleted IS NULL)", (persona_id,))
        row = cursor.fetchone()
        if not row:
            return None
        persona_uuid = row["uuid"]
        if persona_uuid:
            return persona_uuid
        persona_uuid = str(uuid.uuid4())
        updated_at = _now_iso()
        cursor.execute("PRAGMA table_info(personas)")
        columns = {col[1] for col in cursor.fetchall()}

        def _operation() -> None:
            if "updated_at" in columns:
                _execute_with_validation(
                    cursor,
                    "UPDATE personas SET uuid = ?, updated_at = ? WHERE id = ?",
                    (persona_uuid, updated_at, persona_id),
                    "personas.ensure_uuid",
                )
                return
            _execute_with_validation(
                cursor,
                "UPDATE personas SET uuid = ? WHERE id = ?",
                (persona_uuid, persona_id),
                "personas.ensure_uuid_no_updated_at",
            )

        _run_in_transaction_with_retry(self._connection, _operation, context="personas.get_or_create_uuid")
        return persona_uuid
