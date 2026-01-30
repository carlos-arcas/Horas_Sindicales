from __future__ import annotations

import sqlite3
from typing import Iterable

from app.domain.models import Persona, Solicitud
from app.domain.ports import PersonaRepository, SolicitudRepository


def _int_or_zero(value: int | None) -> int:
    return 0 if value is None else int(value)


class PersonaRepositorySQLite(PersonaRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_all(self) -> Iterable[Persona]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min
            FROM personas
            ORDER BY nombre
            """
        )
        rows = cursor.fetchall()
        return [
            Persona(
                id=row["id"],
                nombre=row["nombre"],
                genero=row["genero"],
                horas_mes_min=_int_or_zero(row["horas_mes_min"]),
                horas_ano_min=_int_or_zero(row["horas_ano_min"]),
                horas_jornada_defecto_min=_int_or_zero(row["horas_jornada_defecto_min"]),
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
            )
            for row in rows
        ]

    def get_by_id(self, persona_id: int) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min
            FROM personas
            WHERE id = ?
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
            horas_jornada_defecto_min=_int_or_zero(row["horas_jornada_defecto_min"]),
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
        )

    def get_by_nombre(self, nombre: str) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero,
                   horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                   cuad_lun_man_min, cuad_lun_tar_min,
                   cuad_mar_man_min, cuad_mar_tar_min,
                   cuad_mie_man_min, cuad_mie_tar_min,
                   cuad_jue_man_min, cuad_jue_tar_min,
                   cuad_vie_man_min, cuad_vie_tar_min,
                   cuad_sab_man_min, cuad_sab_tar_min,
                   cuad_dom_man_min, cuad_dom_tar_min
            FROM personas
            WHERE nombre = ?
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
            horas_jornada_defecto_min=_int_or_zero(row["horas_jornada_defecto_min"]),
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
        )

    def create(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO personas (
                nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
                cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                persona.nombre,
                persona.genero,
                persona.horas_mes_min,
                persona.horas_ano_min,
                persona.horas_jornada_defecto_min,
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
            ),
        )
        self._connection.commit()
        return Persona(
            id=cursor.lastrowid,
            nombre=persona.nombre,
            genero=persona.genero,
            horas_mes_min=persona.horas_mes_min,
            horas_ano_min=persona.horas_ano_min,
            horas_jornada_defecto_min=persona.horas_jornada_defecto_min,
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
        )

    def update(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE personas
            SET nombre = ?, genero = ?, horas_mes_min = ?, horas_ano_min = ?, horas_jornada_defecto_min = ?,
                cuad_lun_man_min = ?, cuad_lun_tar_min = ?, cuad_mar_man_min = ?, cuad_mar_tar_min = ?,
                cuad_mie_man_min = ?, cuad_mie_tar_min = ?, cuad_jue_man_min = ?, cuad_jue_tar_min = ?,
                cuad_vie_man_min = ?, cuad_vie_tar_min = ?, cuad_sab_man_min = ?, cuad_sab_tar_min = ?,
                cuad_dom_man_min = ?, cuad_dom_tar_min = ?
            WHERE id = ?
            """,
            (
                persona.nombre,
                persona.genero,
                persona.horas_mes_min,
                persona.horas_ano_min,
                persona.horas_jornada_defecto_min,
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
                persona.id,
            ),
        )
        self._connection.commit()
        return persona


class SolicitudRepositorySQLite(SolicitudRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, observaciones, pdf_path, pdf_hash
            FROM solicitudes
            WHERE persona_id = ?
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
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
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
                       horas_solicitadas_min, observaciones, pdf_path, pdf_hash
                FROM solicitudes
                WHERE persona_id = ?
                  AND strftime('%Y', fecha_pedida) = ?
                ORDER BY fecha_pedida DESC
                """,
                (persona_id, f"{year:04d}"),
            )
        else:
            cursor.execute(
                """
                SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                       horas_solicitadas_min, observaciones, pdf_path, pdf_hash
                FROM solicitudes
                WHERE persona_id = ?
                  AND strftime('%Y', fecha_pedida) = ?
                  AND strftime('%m', fecha_pedida) = ?
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
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
            )
            for row in rows
        ]

    def get_by_id(self, solicitud_id: int) -> Solicitud | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                   horas_solicitadas_min, observaciones, pdf_path, pdf_hash
            FROM solicitudes
            WHERE id = ?
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
            pdf_path=row["pdf_path"],
            pdf_hash=row["pdf_hash"],
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
        cursor.execute(
            """
            INSERT INTO solicitudes (
                persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                horas_solicitadas_min, observaciones, pdf_path, pdf_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                solicitud.persona_id,
                solicitud.fecha_solicitud,
                solicitud.fecha_pedida,
                solicitud.desde_min,
                solicitud.hasta_min,
                int(solicitud.completo),
                solicitud.horas_solicitadas_min,
                solicitud.observaciones,
                solicitud.pdf_path,
                solicitud.pdf_hash,
            ),
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
            pdf_path=solicitud.pdf_path,
            pdf_hash=solicitud.pdf_hash,
        )

    def delete(self, solicitud_id: int) -> None:
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM solicitudes WHERE id = ?", (solicitud_id,))
        self._connection.commit()

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE solicitudes
            SET pdf_path = ?, pdf_hash = ?
            WHERE id = ?
            """,
            (pdf_path, pdf_hash, solicitud_id),
        )
        self._connection.commit()
