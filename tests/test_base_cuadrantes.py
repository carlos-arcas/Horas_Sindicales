from __future__ import annotations

import sqlite3
import unittest

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.application.dto import PersonaDTO
from app.application.use_cases import PersonaUseCases
from app.domain.base_cuadrantes import DEFAULT_BASE_DIAS, DEFAULT_BASE_MAN_MIN, DEFAULT_BASE_TAR_MIN
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import CuadranteRepositorySQLite, PersonaRepositorySQLite


def _build_persona(nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes=0,
        horas_ano=0,
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


class BaseCuadrantesServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        run_migrations(self.connection)
        self.persona_repo = PersonaRepositorySQLite(self.connection)
        self.cuadrante_repo = CuadranteRepositorySQLite(self.connection)
        self.base_service = BaseCuadrantesService(self.persona_repo, self.cuadrante_repo)
        self.use_cases = PersonaUseCases(self.persona_repo, self.base_service)

    def tearDown(self) -> None:
        self.connection.close()

    def test_crea_cuadrantes_base_para_persona_nueva(self) -> None:
        persona = self.use_cases.crear_persona(_build_persona("Delegada Uno"))
        self.assertIsNotNone(persona.id)
        delegada_uuid = self.persona_repo.get_or_create_uuid(persona.id or 0)
        self.assertIsNotNone(delegada_uuid)

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT dia_semana, man_min, tar_min FROM cuadrantes WHERE delegada_uuid = ?",
            (delegada_uuid,),
        )
        rows = cursor.fetchall()
        self.assertEqual(len(rows), len(DEFAULT_BASE_DIAS))
        for row in rows:
            self.assertIn(row["dia_semana"], DEFAULT_BASE_DIAS)
            self.assertEqual(row["man_min"], DEFAULT_BASE_MAN_MIN)
            self.assertEqual(row["tar_min"], DEFAULT_BASE_TAR_MIN)

        persona_actualizada = self.persona_repo.get_by_id(persona.id or 0)
        self.assertIsNotNone(persona_actualizada)
        self.assertEqual(persona_actualizada.cuad_lun_man_min, DEFAULT_BASE_MAN_MIN)
        self.assertEqual(persona_actualizada.cuad_lun_tar_min, DEFAULT_BASE_TAR_MIN)

    def test_no_duplica_cuadrantes_existentes(self) -> None:
        persona = self.use_cases.crear_persona(_build_persona("Delegada Dos"))
        delegada_uuid = self.persona_repo.get_or_create_uuid(persona.id or 0)
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM cuadrantes WHERE delegada_uuid = ?",
            (delegada_uuid,),
        )
        initial_count = cursor.fetchone()["total"]
        self.base_service.ensure_for_persona(persona.id or 0)
        cursor.execute(
            "SELECT COUNT(*) AS total FROM cuadrantes WHERE delegada_uuid = ?",
            (delegada_uuid,),
        )
        after_count = cursor.fetchone()["total"]
        self.assertEqual(initial_count, after_count)


if __name__ == "__main__":
    unittest.main()
