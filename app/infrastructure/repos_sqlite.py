from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Iterable

from app.domain.models import GrupoConfig, Persona, Solicitud
from app.domain.ports import CuadranteRepository, GrupoConfigRepository, PersonaRepository, SolicitudRepository


def _int_or_zero(value: int | None) -> int:
    return 0 if value is None else int(value)


def _bool_from_db(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


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


class PersonaRepositorySQLite(PersonaRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_all(self, include_inactive: bool = False) -> Iterable[Persona]:
        cursor = self._connection.cursor()
        sql = """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   is_active,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min,
                   cuadrante_uniforme, trabaja_finde
            FROM personas
        """
        if not include_inactive:
            sql += " WHERE is_active = 1 AND (deleted = 0 OR deleted IS NULL)"
        else:
            sql += " WHERE deleted = 0 OR deleted IS NULL"
        sql += " ORDER BY nombre"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [
            Persona(
                id=row["id"],
                nombre=row["nombre"],
                genero=row["genero"],
                horas_mes_min=_int_or_zero(row["horas_mes_min"]),
                horas_ano_min=_int_or_zero(row["horas_ano_min"]),
                is_active=_bool_from_db(row["is_active"]) if "is_active" in row.keys() else True,
                cuad_lun_man_min=_int_or_zero(row["cuad_lun_man_min"]),
                cuad_lun_tar_min=_int_or_zero(row["cuad_lun_tar_min"]),
                cuad_mar_man_min=_int_or_zero(row["cuad_mar_man_min"]),
                cuad_mar_tar_min=_int_or_zero(row["cuad_mar_tar_min"]),
                cuad_mie_man_min=_int_or_zero(row["cuad_mie_man_min"]),
                cuad_mie_tar_min=_int_or_zero(row["cuad_mie_tar_min"]),
                cuad_jue_man_min=_int_or_zero(row["cuad_jue_man_min"]),
                cuad_jue_tar_min=_int_or_zero(row["cuad_jue_tar_min"]),
                cuad_vie_man_min=_int_or_zero(row["cuad_vie_man_min"]),
                cuad_vie_tar_min=_int_or_zero(row["cuad_vie_tar_min"]),
                cuad_sab_man_min=_int_or_zero(row["cuad_sab_man_min"]),
                cuad_sab_tar_min=_int_or_zero(row["cuad_sab_tar_min"]),
                cuad_dom_man_min=_int_or_zero(row["cuad_dom_man_min"]),
                cuad_dom_tar_min=_int_or_zero(row["cuad_dom_tar_min"]),
                cuadrante_uniforme=_bool_from_db(row["cuadrante_uniforme"]) if "cuadrante_uniforme" in row.keys() else False,
                trabaja_finde=_bool_from_db(row["trabaja_finde"]) if "trabaja_finde" in row.keys() else False,
            )
            for row in rows
        ]

    def get_by_id(self, persona_id: int) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   is_active,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min,
                   cuadrante_uniforme, trabaja_finde
            FROM personas
            WHERE id = ? AND (deleted = 0 OR deleted IS NULL)
            """,
            (persona_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Persona(
            id=row["id"],
            nombre=row["nombre"],
            genero=row["genero"],
            horas_mes_min=_int_or_zero(row["horas_mes_min"]),
            horas_ano_min=_int_or_zero(row["horas_ano_min"]),
            is_active=_bool_from_db(row["is_active"]) if "is_active" in row.keys() else True,
            cuad_lun_man_min=_int_or_zero(row["cuad_lun_man_min"]),
            cuad_lun_tar_min=_int_or_zero(row["cuad_lun_tar_min"]),
            cuad_mar_man_min=_int_or_zero(row["cuad_mar_man_min"]),
            cuad_mar_tar_min=_int_or_zero(row["cuad_mar_tar_min"]),
            cuad_mie_man_min=_int_or_zero(row["cuad_mie_man_min"]),
            cuad_mie_tar_min=_int_or_zero(row["cuad_mie_tar_min"]),
            cuad_jue_man_min=_int_or_zero(row["cuad_jue_man_min"]),
            cuad_jue_tar_min=_int_or_zero(row["cuad_jue_tar_min"]),
            cuad_vie_man_min=_int_or_zero(row["cuad_vie_man_min"]),
            cuad_vie_tar_min=_int_or_zero(row["cuad_vie_tar_min"]),
            cuad_sab_man_min=_int_or_zero(row["cuad_sab_man_min"]),
            cuad_sab_tar_min=_int_or_zero(row["cuad_sab_tar_min"]),
            cuad_dom_man_min=_int_or_zero(row["cuad_dom_man_min"]),
            cuad_dom_tar_min=_int_or_zero(row["cuad_dom_tar_min"]),
            cuadrante_uniforme=_bool_from_db(row["cuadrante_uniforme"]) if "cuadrante_uniforme" in row.keys() else False,
            trabaja_finde=_bool_from_db(row["trabaja_finde"]) if "trabaja_finde" in row.keys() else False,
        )

    def get_by_nombre(self, nombre: str) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   is_active,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min,
                   cuadrante_uniforme, trabaja_finde
            FROM personas
            WHERE nombre = ? AND (deleted = 0 OR deleted IS NULL)
            """,
            (nombre,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Persona(
            id=row["id"],
            nombre=row["nombre"],
            genero=row["genero"],
            horas_mes_min=_int_or_zero(row["horas_mes_min"]),
            horas_ano_min=_int_or_zero(row["horas_ano_min"]),
            is_active=_bool_from_db(row["is_active"]) if "is_active" in row.keys() else True,
            cuad_lun_man_min=_int_or_zero(row["cuad_lun_man_min"]),
            cuad_lun_tar_min=_int_or_zero(row["cuad_lun_tar_min"]),
            cuad_mar_man_min=_int_or_zero(row["cuad_mar_man_min"]),
            cuad_mar_tar_min=_int_or_zero(row["cuad_mar_tar_min"]),
            cuad_mie_man_min=_int_or_zero(row["cuad_mie_man_min"]),
            cuad_mie_tar_min=_int_or_zero(row["cuad_mie_tar_min"]),
            cuad_jue_man_min=_int_or_zero(row["cuad_jue_man_min"]),
            cuad_jue_tar_min=_int_or_zero(row["cuad_jue_tar_min"]),
            cuad_vie_man_min=_int_or_zero(row["cuad_vie_man_min"]),
            cuad_vie_tar_min=_int_or_zero(row["cuad_vie_tar_min"]),
            cuad_sab_man_min=_int_or_zero(row["cuad_sab_man_min"]),
            cuad_sab_tar_min=_int_or_zero(row["cuad_sab_tar_min"]),
            cuad_dom_man_min=_int_or_zero(row["cuad_dom_man_min"]),
            cuad_dom_tar_min=_int_or_zero(row["cuad_dom_tar_min"]),
            cuadrante_uniforme=_bool_from_db(row["cuadrante_uniforme"]) if "cuadrante_uniforme" in row.keys() else False,
            trabaja_finde=_bool_from_db(row["trabaja_finde"]) if "trabaja_finde" in row.keys() else False,
        )

    def create(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        persona_uuid = str(uuid.uuid4())
        updated_at = _now_iso()
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
            (
                persona_uuid,
                persona.nombre,
                persona.genero,
                persona.horas_mes_min,
                persona.horas_ano_min,
                0,
                1 if persona.is_active else 0,
                persona.cuad_lun_man_min,
                persona.cuad_lun_tar_min,
                persona.cuad_mar_man_min,
                persona.cuad_mar_tar_min,
                persona.cuad_mie_man_min,
                persona.cuad_mie_tar_min,
                persona.cuad_jue_man_min,
                persona.cuad_jue_tar_min,
                persona.cuad_vie_man_min,
                persona.cuad_vie_tar_min,
                persona.cuad_sab_man_min,
                persona.cuad_sab_tar_min,
                persona.cuad_dom_man_min,
                persona.cuad_dom_tar_min,
                1 if persona.cuadrante_uniforme else 0,
                1 if persona.trabaja_finde else 0,
                updated_at,
                0,
            ),
            "personas.insert",
        )
        self._connection.commit()
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
            (
                persona.nombre,
                persona.genero,
                persona.horas_mes_min,
                persona.horas_ano_min,
                0,
                1 if persona.is_active else 0,
                persona.cuad_lun_man_min,
                persona.cuad_lun_tar_min,
                persona.cuad_mar_man_min,
                persona.cuad_mar_tar_min,
                persona.cuad_mie_man_min,
                persona.cuad_mie_tar_min,
                persona.cuad_jue_man_min,
                persona.cuad_jue_tar_min,
                persona.cuad_vie_man_min,
                persona.cuad_vie_tar_min,
                persona.cuad_sab_man_min,
                persona.cuad_sab_tar_min,
                persona.cuad_dom_man_min,
                persona.cuad_dom_tar_min,
                1 if persona.cuadrante_uniforme else 0,
                1 if persona.trabaja_finde else 0,
                updated_at,
                persona.id,
            ),
            "personas.update",
        )
        self._connection.commit()
        return persona

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
        if "updated_at" in columns:
            _execute_with_validation(
                cursor,
                "UPDATE personas SET uuid = ?, updated_at = ? WHERE id = ?",
                (persona_uuid, updated_at, persona_id),
                "personas.ensure_uuid",
            )
        else:
            _execute_with_validation(
                cursor,
                "UPDATE personas SET uuid = ? WHERE id = ?",
                (persona_uuid, persona_id),
                "personas.ensure_uuid_no_updated_at",
            )
        self._connection.commit()
        return persona_uuid


class CuadranteRepositorySQLite(CuadranteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def exists_for_delegada(self, delegada_uuid: str, dia_semana: str) -> bool:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM cuadrantes
            WHERE delegada_uuid = ?
              AND dia_semana = ?
              AND (deleted = 0 OR deleted IS NULL)
            LIMIT 1
            """,
            (delegada_uuid, dia_semana),
        )
        return cursor.fetchone() is not None

    def create(self, delegada_uuid: str, dia_semana: str, man_min: int, tar_min: int) -> None:
        cursor = self._connection.cursor()
        _execute_with_validation(
            cursor,
            """
            INSERT INTO cuadrantes (uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, deleted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (str(uuid.uuid4()), delegada_uuid, dia_semana, man_min, tar_min, _now_iso()),
            "cuadrantes.insert",
        )
        self._connection.commit()


class SolicitudRepositorySQLite(SolicitudRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
            FROM solicitudes
            WHERE persona_id = ?
              AND generated = 1
              AND (deleted = 0 OR deleted IS NULL)
            ORDER BY fecha_pedida DESC
            """,
            (persona_id,),
        )
        rows = cursor.fetchall()
        return [
            Solicitud(
                id=row["id"],
                persona_id=row["persona_id"],
                fecha_solicitud=row["fecha_solicitud"],
                fecha_pedida=row["fecha_pedida"],
                desde_min=row["desde_min"],
                hasta_min=row["hasta_min"],
                completo=bool(row["completo"]),
                horas_solicitadas_min=_int_or_zero(row["horas_solicitadas_min"]),
                observaciones=row["observaciones"],
                notas=row["notas"],
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
                generated=bool(row["generated"]),
            )
            for row in rows
        ]

    def list_by_persona_and_period(
        self, persona_id: int, year: int, month: int | None = None
    ) -> Iterable[Solicitud]:
        cursor = self._connection.cursor()
        if month is None:
            cursor.execute(
                """
                SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                       horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
                FROM solicitudes
                WHERE persona_id = ?
                  AND strftime('%Y', fecha_pedida) = ?
                  AND generated = 1
                  AND (deleted = 0 OR deleted IS NULL)
                ORDER BY fecha_pedida DESC
                """,
                (persona_id, f"{year:04d}"),
            )
        else:
            cursor.execute(
                """
                SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                       horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
                FROM solicitudes
                WHERE persona_id = ?
                  AND strftime('%Y', fecha_pedida) = ?
                  AND strftime('%m', fecha_pedida) = ?
                  AND generated = 1
                  AND (deleted = 0 OR deleted IS NULL)
                ORDER BY fecha_pedida DESC
                """,
                (persona_id, f"{year:04d}", f"{month:02d}"),
            )
        rows = cursor.fetchall()
        return [
            Solicitud(
                id=row["id"],
                persona_id=row["persona_id"],
                fecha_solicitud=row["fecha_solicitud"],
                fecha_pedida=row["fecha_pedida"],
                desde_min=row["desde_min"],
                hasta_min=row["hasta_min"],
                completo=bool(row["completo"]),
                horas_solicitadas_min=_int_or_zero(row["horas_solicitadas_min"]),
                observaciones=row["observaciones"],
                notas=row["notas"],
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
                generated=bool(row["generated"]),
            )
            for row in rows
        ]

    def list_by_persona_and_fecha(
        self, persona_id: int, fecha_pedida: str
    ) -> Iterable[Solicitud]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
            FROM solicitudes
            WHERE persona_id = ?
              AND fecha_pedida = ?
              AND generated = 1
              AND (deleted = 0 OR deleted IS NULL)
            ORDER BY fecha_pedida DESC
            """,
            (persona_id, fecha_pedida),
        )
        rows = cursor.fetchall()
        return [
            Solicitud(
                id=row["id"],
                persona_id=row["persona_id"],
                fecha_solicitud=row["fecha_solicitud"],
                fecha_pedida=row["fecha_pedida"],
                desde_min=row["desde_min"],
                hasta_min=row["hasta_min"],
                completo=bool(row["completo"]),
                horas_solicitadas_min=_int_or_zero(row["horas_solicitadas_min"]),
                observaciones=row["observaciones"],
                notas=row["notas"],
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
                generated=bool(row["generated"]),
            )
            for row in rows
        ]

    def get_by_id(self, solicitud_id: int) -> Solicitud | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
            FROM solicitudes
            WHERE id = ? AND (deleted = 0 OR deleted IS NULL)
            """,
            (solicitud_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Solicitud(
            id=row["id"],
            persona_id=row["persona_id"],
            fecha_solicitud=row["fecha_solicitud"],
            fecha_pedida=row["fecha_pedida"],
            desde_min=row["desde_min"],
            hasta_min=row["hasta_min"],
            completo=bool(row["completo"]),
            horas_solicitadas_min=_int_or_zero(row["horas_solicitadas_min"]),
            observaciones=row["observaciones"],
            notas=row["notas"],
            pdf_path=row["pdf_path"],
            pdf_hash=row["pdf_hash"],
            generated=bool(row["generated"]),
        )

    def exists_duplicate(
        self,
        persona_id: int,
        fecha_pedida: str,
        desde_min: int | None,
        hasta_min: int | None,
        completo: bool,
    ) -> bool:
        cursor = self._connection.cursor()
        clauses = [
            "persona_id = ?",
            "fecha_pedida = ?",
            "completo = ?",
            "(deleted = 0 OR deleted IS NULL)",
        ]
        params: list[object] = [persona_id, fecha_pedida, int(completo)]
        if desde_min is None:
            clauses.append("desde_min IS NULL")
        else:
            clauses.append("desde_min = ?")
            params.append(desde_min)
        if hasta_min is None:
            clauses.append("hasta_min IS NULL")
        else:
            clauses.append("hasta_min = ?")
            params.append(hasta_min)
        cursor.execute(
            f"""
            SELECT 1
            FROM solicitudes
            WHERE {' AND '.join(clauses)}
            LIMIT 1
            """,
            params,
        )
        return cursor.fetchone() is not None

    def create(self, solicitud: Solicitud) -> Solicitud:
        cursor = self._connection.cursor()
        solicitud_uuid = str(uuid.uuid4())
        created_at = _now_iso()
        _execute_with_validation(
            cursor,
            """
            INSERT INTO solicitudes (
                uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated, created_at, updated_at, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                solicitud_uuid,
                solicitud.persona_id,
                solicitud.fecha_solicitud,
                solicitud.fecha_pedida,
                solicitud.desde_min,
                solicitud.hasta_min,
                int(solicitud.completo),
                solicitud.horas_solicitadas_min,
                solicitud.observaciones,
                solicitud.notas or "",
                solicitud.pdf_path,
                solicitud.pdf_hash,
                0,
                created_at,
                created_at,
                0,
            ),
            "solicitudes.insert",
        )
        self._connection.commit()
        return Solicitud(
            id=cursor.lastrowid,
            persona_id=solicitud.persona_id,
            fecha_solicitud=solicitud.fecha_solicitud,
            fecha_pedida=solicitud.fecha_pedida,
            desde_min=solicitud.desde_min,
            hasta_min=solicitud.hasta_min,
            completo=solicitud.completo,
            horas_solicitadas_min=solicitud.horas_solicitadas_min,
            observaciones=solicitud.observaciones,
            notas=solicitud.notas or "",
            pdf_path=solicitud.pdf_path,
            pdf_hash=solicitud.pdf_hash,
            generated=False,
        )

    def delete(self, solicitud_id: int) -> None:
        cursor = self._connection.cursor()
        updated_at = _now_iso()
        _execute_with_validation(
            cursor,
            """
            UPDATE solicitudes
            SET deleted = 1, updated_at = ?
            WHERE id = ?
            """,
            (updated_at, solicitud_id),
            "solicitudes.delete",
        )
        self._connection.commit()

    def delete_by_ids(self, solicitud_ids: Iterable[int]) -> None:
        ids = list(solicitud_ids)
        if not ids:
            return
        cursor = self._connection.cursor()
        placeholders = ",".join("?" for _ in ids)
        sql = f"UPDATE solicitudes SET deleted = 1, updated_at = ? WHERE id IN ({placeholders})"
        _execute_with_validation(cursor, sql, [_now_iso(), *ids], "solicitudes.delete_by_ids")
        self._connection.commit()

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        cursor = self._connection.cursor()
        updated_at = _now_iso()
        _execute_with_validation(
            cursor,
            """
            UPDATE solicitudes
            SET pdf_path = ?, pdf_hash = ?, generated = 1, updated_at = ?
            WHERE id = ?
            """,
            (pdf_path, pdf_hash, updated_at, solicitud_id),
            "solicitudes.update_pdf_info",
        )
        self._connection.commit()


class GrupoConfigRepositorySQLite(GrupoConfigRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self) -> GrupoConfig | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre_grupo, bolsa_anual_grupo_min, pdf_logo_path,
                   pdf_intro_text, pdf_include_hours_in_horario
            FROM grupo_config
            WHERE id = 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        return GrupoConfig(
            id=row["id"],
            nombre_grupo=row["nombre_grupo"],
            bolsa_anual_grupo_min=_int_or_zero(row["bolsa_anual_grupo_min"]),
            pdf_logo_path=row["pdf_logo_path"],
            pdf_intro_text=row["pdf_intro_text"],
            pdf_include_hours_in_horario=_bool_from_db(row["pdf_include_hours_in_horario"]),
        )

    def upsert(self, config: GrupoConfig) -> GrupoConfig:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO grupo_config (
                id, nombre_grupo, bolsa_anual_grupo_min, pdf_logo_path,
                pdf_intro_text, pdf_include_hours_in_horario
            ) VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nombre_grupo = excluded.nombre_grupo,
                bolsa_anual_grupo_min = excluded.bolsa_anual_grupo_min,
                pdf_logo_path = excluded.pdf_logo_path,
                pdf_intro_text = excluded.pdf_intro_text,
                pdf_include_hours_in_horario = excluded.pdf_include_hours_in_horario
            """,
            (
                config.nombre_grupo,
                config.bolsa_anual_grupo_min,
                config.pdf_logo_path,
                config.pdf_intro_text,
                None
                if config.pdf_include_hours_in_horario is None
                else int(config.pdf_include_hours_in_horario),
            ),
        )
        self._connection.commit()
        return GrupoConfig(
            id=1,
            nombre_grupo=config.nombre_grupo,
            bolsa_anual_grupo_min=config.bolsa_anual_grupo_min,
            pdf_logo_path=config.pdf_logo_path,
            pdf_intro_text=config.pdf_intro_text,
            pdf_include_hours_in_horario=config.pdf_include_hours_in_horario,
        )
