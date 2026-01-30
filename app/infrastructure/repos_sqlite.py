from __future__ import annotations

import sqlite3
from typing import Iterable

from app.domain.models import Persona, Solicitud
from app.domain.ports import PersonaRepository, SolicitudRepository


class PersonaRepositorySQLite(PersonaRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_all(self) -> Iterable[Persona]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero, horas_mes, horas_ano, horas_jornada_defecto,
                   cuad_lun, cuad_mar, cuad_mie, cuad_jue, cuad_vie, cuad_sab, cuad_dom
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
                horas_mes=row["horas_mes"],
                horas_ano=row["horas_ano"],
                horas_jornada_defecto=row["horas_jornada_defecto"],
                cuad_lun=row["cuad_lun"],
                cuad_mar=row["cuad_mar"],
                cuad_mie=row["cuad_mie"],
                cuad_jue=row["cuad_jue"],
                cuad_vie=row["cuad_vie"],
                cuad_sab=row["cuad_sab"],
                cuad_dom=row["cuad_dom"],
            )
            for row in rows
        ]

    def get_by_nombre(self, nombre: str) -> Persona | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, nombre, genero, horas_mes, horas_ano, horas_jornada_defecto,
                   cuad_lun, cuad_mar, cuad_mie, cuad_jue, cuad_vie, cuad_sab, cuad_dom
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
            horas_mes=row["horas_mes"],
            horas_ano=row["horas_ano"],
            horas_jornada_defecto=row["horas_jornada_defecto"],
            cuad_lun=row["cuad_lun"],
            cuad_mar=row["cuad_mar"],
            cuad_mie=row["cuad_mie"],
            cuad_jue=row["cuad_jue"],
            cuad_vie=row["cuad_vie"],
            cuad_sab=row["cuad_sab"],
            cuad_dom=row["cuad_dom"],
        )

    def create(self, persona: Persona) -> Persona:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO personas (
                nombre, genero, horas_mes, horas_ano, horas_jornada_defecto,
                cuad_lun, cuad_mar, cuad_mie, cuad_jue, cuad_vie, cuad_sab, cuad_dom
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                persona.nombre,
                persona.genero,
                persona.horas_mes,
                persona.horas_ano,
                persona.horas_jornada_defecto,
                persona.cuad_lun,
                persona.cuad_mar,
                persona.cuad_mie,
                persona.cuad_jue,
                persona.cuad_vie,
                persona.cuad_sab,
                persona.cuad_dom,
            ),
        )
        self._connection.commit()
        return Persona(
            id=cursor.lastrowid,
            nombre=persona.nombre,
            genero=persona.genero,
            horas_mes=persona.horas_mes,
            horas_ano=persona.horas_ano,
            horas_jornada_defecto=persona.horas_jornada_defecto,
            cuad_lun=persona.cuad_lun,
            cuad_mar=persona.cuad_mar,
            cuad_mie=persona.cuad_mie,
            cuad_jue=persona.cuad_jue,
            cuad_vie=persona.cuad_vie,
            cuad_sab=persona.cuad_sab,
            cuad_dom=persona.cuad_dom,
        )


class SolicitudRepositorySQLite(SolicitudRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, persona_id, fecha_solicitud, fecha_pedida, desde, hasta, completo,
                   horas, observaciones, pdf_path, pdf_hash
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
                desde=row["desde"],
                hasta=row["hasta"],
                completo=bool(row["completo"]),
                horas=row["horas"],
                observaciones=row["observaciones"],
                pdf_path=row["pdf_path"],
                pdf_hash=row["pdf_hash"],
            )
            for row in rows
        ]

    def create(self, solicitud: Solicitud) -> Solicitud:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO solicitudes (
                persona_id, fecha_solicitud, fecha_pedida, desde, hasta, completo,
                horas, observaciones, pdf_path, pdf_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                solicitud.persona_id,
                solicitud.fecha_solicitud,
                solicitud.fecha_pedida,
                solicitud.desde,
                solicitud.hasta,
                int(solicitud.completo),
                solicitud.horas,
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
            desde=solicitud.desde,
            hasta=solicitud.hasta,
            completo=solicitud.completo,
            horas=solicitud.horas,
            observaciones=solicitud.observaciones,
            pdf_path=solicitud.pdf_path,
            pdf_hash=solicitud.pdf_hash,
        )
