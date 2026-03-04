from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.domain.reportes_contenido import FiltroReportes, PeticionPaginada, ReporteContenido
from app.infrastructure.migrations import run_migrations
from app.infrastructure.reportes_sqlite import RecursosModeracionSQLite, ReportesRepositorioSQLite


def _crear_conexion() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    run_migrations(connection)
    return connection


def _insertar_solicitud(connection: sqlite3.Connection, uuid_recurso: str) -> None:
    connection.execute(
        """
        INSERT INTO personas(nombre, genero, horas_mes_min, horas_ano_min, is_active)
        VALUES ('Persona Test', 'F', 60, 600, 1)
        """
    )
    persona_id = connection.execute("SELECT id FROM personas LIMIT 1").fetchone()["id"]
    connection.execute(
        """
        INSERT INTO solicitudes(
            persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
            horas_solicitadas_min, generated, uuid, deleted
        ) VALUES (?, '2026-03-01', '2026-03-01', 480, 540, 0, 60, 1, ?, 0)
        """,
        (persona_id, uuid_recurso),
    )
    connection.commit()


def test_unique_idempotencia_no_duplica_pendiente() -> None:
    conn = _crear_conexion()
    repo = ReportesRepositorioSQLite(conn)
    base = ReporteContenido(
        reporte_id="rep-1",
        denunciante_id="u-1",
        recurso_tipo="publicacion",
        recurso_id="pub-1",
        motivo="spam",
        detalle=None,
        estado="pendiente",
        creado_en=datetime.now(timezone.utc),
    )
    assert repo.crear_si_no_existe_pendiente(base) is True
    repetido = ReporteContenido(
        reporte_id="rep-2",
        denunciante_id="u-1",
        recurso_tipo="publicacion",
        recurso_id="pub-1",
        motivo="spam",
        detalle=None,
        estado="pendiente",
        creado_en=datetime.now(timezone.utc),
    )
    assert repo.crear_si_no_existe_pendiente(repetido) is False


def test_filtros_paginacion_y_orden_estable() -> None:
    conn = _crear_conexion()
    repo = ReportesRepositorioSQLite(conn)
    now = datetime.now(timezone.utc)
    for idx in range(3):
        repo.crear_si_no_existe_pendiente(
            ReporteContenido(
                reporte_id=f"rep-{idx}",
                denunciante_id="u-1",
                recurso_tipo="publicacion",
                recurso_id=f"pub-{idx}",
                motivo="spam",
                detalle=None,
                estado="pendiente",
                creado_en=now,
            )
        )
    items, total = repo.listar_admin(FiltroReportes(estado="pendiente"), PeticionPaginada(limit=2, offset=0))
    assert total == 3
    assert len(items) == 2


def test_ocultar_recurso_cambia_deleted_en_solicitudes() -> None:
    conn = _crear_conexion()
    _insertar_solicitud(conn, "pub-visible")
    recursos = RecursosModeracionSQLite(conn)
    assert recursos.ocultar_recurso("publicacion", "pub-visible") is True
    deleted = conn.execute("SELECT deleted FROM solicitudes WHERE uuid = 'pub-visible'").fetchone()["deleted"]
    assert int(deleted) == 1
