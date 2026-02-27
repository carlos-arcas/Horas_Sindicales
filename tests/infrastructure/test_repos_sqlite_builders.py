from __future__ import annotations

import sqlite3

from app.domain.models import Persona, Solicitud
from app.infrastructure.repos_sqlite import SolicitudRepositorySQLite
from app.infrastructure.repos_sqlite_builders import (
    build_period_filters,
    build_soft_delete_many_sql,
    persona_insert_params,
    persona_update_params,
    solicitud_insert_params,
)


def _persona_demo() -> Persona:
    return Persona(
        id=17,
        nombre="Ana",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=True,
        cuad_lun_man_min=240,
        cuad_lun_tar_min=240,
        cuad_mar_man_min=240,
        cuad_mar_tar_min=240,
        cuad_mie_man_min=240,
        cuad_mie_tar_min=240,
        cuad_jue_man_min=240,
        cuad_jue_tar_min=240,
        cuad_vie_man_min=240,
        cuad_vie_tar_min=240,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
        cuadrante_uniforme=True,
        trabaja_finde=False,
    )


def test_builders_persona_insert_update_respetan_orden_de_parametros() -> None:
    persona = _persona_demo()

    insert_params = persona_insert_params(persona, "uuid-demo", "2025-01-01T00:00:00Z")
    update_params = persona_update_params(persona, "2025-01-01T00:00:00Z")

    assert insert_params[:3] == ("uuid-demo", "Ana", "F")
    assert insert_params[-2:] == ("2025-01-01T00:00:00Z", 0)
    assert len(insert_params) == 25

    assert update_params[:2] == ("Ana", "F")
    assert update_params[-2:] == ("2025-01-01T00:00:00Z", 17)
    assert len(update_params) == 24


def test_builders_solicitud_insert_y_periodo() -> None:
    solicitud = Solicitud(
        id=None,
        persona_id=9,
        fecha_solicitud="2025-03-01",
        fecha_pedida="2025-03-15",
        desde_min=540,
        hasta_min=600,
        completo=False,
        horas_solicitadas_min=60,
        observaciones="obs",
        notas=None,
        pdf_path=None,
        pdf_hash=None,
        generated=False,
    )

    params = solicitud_insert_params(solicitud, "sol-uuid", "2025-03-01T10:00:00Z")
    assert params[0] == "sol-uuid"
    assert params[9] == ""
    assert params[-1] == 0
    assert len(params) == 16

    where_year, values_year = build_period_filters(2025)
    where_month, values_month = build_period_filters(2025, 3)
    assert where_year == "strftime('%Y', fecha_pedida) = ?"
    assert values_year == ("2025",)
    assert "strftime('%m', fecha_pedida) = ?" in where_month
    assert values_month == ("2025", "03")


def test_builders_delete_many_sql_no_duplica_ids() -> None:
    sql, ids = build_soft_delete_many_sql([7, 8, 9])
    assert sql.endswith("WHERE id IN (?,?,?)")
    assert ids == [7, 8, 9]


def test_delete_by_ids_realiza_soft_delete_solo_en_ids_indicados(connection: sqlite3.Connection) -> None:
    repo = SolicitudRepositorySQLite(connection)

    connection.execute(
        "INSERT INTO personas (id, uuid, nombre, genero, horas_mes_min, horas_ano_min, is_active, deleted) VALUES (1, 'u-1', 'Ana', 'F', 1, 1, 1, 0)"
    )
    for idx in (101, 102, 103):
        connection.execute(
            """
            INSERT INTO solicitudes (
                id, uuid, persona_id, fecha_solicitud, fecha_pedida, completo,
                horas_solicitadas_min, generated, deleted
            ) VALUES (?, ?, 1, '2025-01-01', '2025-01-01', 1, 60, 0, 0)
            """,
            (idx, f"sol-{idx}"),
        )
    connection.commit()

    repo.delete_by_ids([101, 103])

    estados = {
        row["id"]: row["deleted"]
        for row in connection.execute(
            "SELECT id, deleted FROM solicitudes WHERE id IN (101, 102, 103) ORDER BY id"
        ).fetchall()
    }
    assert estados == {101: 1, 102: 0, 103: 1}
