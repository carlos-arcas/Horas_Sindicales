from __future__ import annotations

import sqlite3

from app.domain.models import Persona
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite_personas import PersonaRepositorySQLite


MALICIOUS_PAYLOADS = [
    "x'); DROP TABLE personas; --",
    "sudo delete table estudiantes on cascade",
]


def _build_persona(nombre: str) -> Persona:
    return Persona(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes_min=60,
        horas_ano_min=720,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_sql_injection_payloads_do_not_drop_tables(tmp_path) -> None:
    db_path = tmp_path / "security.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    run_migrations(connection)

    repository = PersonaRepositorySQLite(connection)
    for payload in MALICIOUS_PAYLOADS:
        repository.create(_build_persona(payload))

    personas_count = connection.execute("SELECT count(*) AS total FROM personas").fetchone()["total"]
    solicitudes_count = connection.execute("SELECT count(*) AS total FROM solicitudes").fetchone()["total"]

    assert personas_count >= len(MALICIOUS_PAYLOADS)
    assert solicitudes_count >= 0
