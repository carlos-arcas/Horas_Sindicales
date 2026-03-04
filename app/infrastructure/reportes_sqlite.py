from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.application.reportes.puertos import EventoAuditoriaSeguridad
from app.domain.reportes_contenido import FiltroReportes, PeticionPaginada, ReporteContenido


class ReportesRepositorioSQLite:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row

    def crear_si_no_existe_pendiente(self, reporte: ReporteContenido) -> bool:
        cursor = self._connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO reportes_contenido (
                    reporte_uuid, denunciante_id, recurso_tipo, recurso_id, motivo, detalle, estado, fecha_creacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reporte.reporte_id,
                    reporte.denunciante_id,
                    reporte.recurso_tipo,
                    reporte.recurso_id,
                    reporte.motivo,
                    reporte.detalle,
                    reporte.estado,
                    reporte.creado_en.isoformat(),
                ),
            )
            self._connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def listar_admin(self, filtro: FiltroReportes, paginacion: PeticionPaginada) -> tuple[list[ReporteContenido], int]:
        where = ["1=1"]
        params: list[object] = []
        if filtro.estado:
            where.append("estado = ?")
            params.append(filtro.estado)
        if filtro.motivo:
            where.append("motivo = ?")
            params.append(filtro.motivo)
        if filtro.recurso_tipo:
            where.append("recurso_tipo = ?")
            params.append(filtro.recurso_tipo)
        where_sql = " AND ".join(where)

        cursor = self._connection.cursor()
        cursor.execute(f"SELECT COUNT(1) AS total FROM reportes_contenido WHERE {where_sql}", tuple(params))
        total = int(cursor.fetchone()["total"])

        cursor.execute(
            f"""
            SELECT reporte_uuid, denunciante_id, recurso_tipo, recurso_id, motivo, detalle, estado, fecha_creacion
            FROM reportes_contenido
            WHERE {where_sql}
            ORDER BY fecha_creacion DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, paginacion.limit, paginacion.offset]),
        )
        items = [self._to_domain(row) for row in cursor.fetchall()]
        return items, total

    def obtener_por_id(self, reporte_id: str) -> ReporteContenido | None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT reporte_uuid, denunciante_id, recurso_tipo, recurso_id, motivo, detalle, estado, fecha_creacion
            FROM reportes_contenido WHERE reporte_uuid = ? LIMIT 1
            """,
            (reporte_id,),
        )
        row = cursor.fetchone()
        return self._to_domain(row) if row else None

    def marcar_resuelto(self, reporte_id: str, admin_id: str, accion: str, comentario_admin: str | None) -> bool:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE reportes_contenido
            SET estado = CASE WHEN ? = 'descartar' THEN 'descartado' ELSE 'resuelto' END,
                accion_moderacion = ?,
                admin_resolutor_id = ?,
                comentario_admin = ?,
                fecha_resolucion = ?
            WHERE reporte_uuid = ? AND estado = 'pendiente'
            """,
            (accion, accion, admin_id, comentario_admin, datetime.now(timezone.utc).isoformat(), reporte_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _to_domain(row: sqlite3.Row) -> ReporteContenido:
        return ReporteContenido(
            reporte_id=str(row["reporte_uuid"]),
            denunciante_id=str(row["denunciante_id"]),
            recurso_tipo=str(row["recurso_tipo"]),
            recurso_id=str(row["recurso_id"]),
            motivo=str(row["motivo"]),
            detalle=row["detalle"],
            estado=str(row["estado"]),
            creado_en=datetime.fromisoformat(str(row["fecha_creacion"]).replace("Z", "+00:00")),
        )


class RecursosModeracionSQLite:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def existe_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        tabla = "solicitudes" if recurso_tipo == "publicacion" else "conflicts"
        cursor = self._connection.cursor()
        cursor.execute(f"SELECT 1 FROM {tabla} WHERE uuid = ? LIMIT 1", (recurso_id,))
        return cursor.fetchone() is not None

    def ocultar_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        tabla = "solicitudes" if recurso_tipo == "publicacion" else "conflicts"
        cursor = self._connection.cursor()
        cursor.execute(f"UPDATE {tabla} SET deleted = 1 WHERE uuid = ? AND (deleted = 0 OR deleted IS NULL)", (recurso_id,))
        self._connection.commit()
        return cursor.rowcount > 0


class AuditoriaSeguridadSQLite:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def registrar(self, evento: EventoAuditoriaSeguridad) -> None:
        self._connection.execute(
            """
            INSERT INTO auditoria_seguridad(
                tipo_evento, resultado, reason_code, actor_id, recurso_tipo, recurso_id, fecha_evento
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evento.tipo_evento,
                evento.resultado,
                evento.reason_code,
                evento.actor_id,
                evento.recurso_tipo,
                evento.recurso_id,
                evento.fecha.isoformat(),
            ),
        )
        self._connection.commit()
