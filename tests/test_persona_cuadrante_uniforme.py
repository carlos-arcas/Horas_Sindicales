from __future__ import annotations

import sqlite3
import unittest

from app.application.dto import PersonaDTO, SolicitudDTO
from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.infrastructure.migrations import run_migrations
from app.domain.services import BusinessRuleError
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


def _build_persona() -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre="Delegada Uniforme",
        genero="F",
        horas_mes=0,
        horas_ano=0,
        is_active=True,
        cuad_lun_man_min=120,
        cuad_lun_tar_min=180,
        cuad_mar_man_min=1,
        cuad_mar_tar_min=2,
        cuad_mie_man_min=3,
        cuad_mie_tar_min=4,
        cuad_jue_man_min=5,
        cuad_jue_tar_min=6,
        cuad_vie_man_min=7,
        cuad_vie_tar_min=8,
        cuad_sab_man_min=30,
        cuad_sab_tar_min=45,
        cuad_dom_man_min=15,
        cuad_dom_tar_min=25,
        cuadrante_uniforme=True,
        trabaja_finde=True,
    )


class PersonaCuadranteUniformeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        run_migrations(self.connection)
        self.repo = PersonaRepositorySQLite(self.connection)
        self.use_cases = PersonaUseCases(self.repo)

    def tearDown(self) -> None:
        self.connection.close()

    def test_crear_persona_uniforme_replica_lunes_en_laborables(self) -> None:
        creada = self.use_cases.crear_persona(_build_persona())
        self.assertTrue(creada.cuadrante_uniforme)
        self.assertEqual(creada.cuad_lun_man_min, 120)
        self.assertEqual(creada.cuad_lun_tar_min, 180)
        self.assertEqual(creada.cuad_mar_man_min, 120)
        self.assertEqual(creada.cuad_mar_tar_min, 180)
        self.assertEqual(creada.cuad_mie_man_min, 120)
        self.assertEqual(creada.cuad_jue_tar_min, 180)
        self.assertEqual(creada.cuad_vie_man_min, 120)

    def test_editar_persona_no_uniforme_respeta_valores_por_dia(self) -> None:
        creada = self.use_cases.crear_persona(_build_persona())
        editada = PersonaDTO(
            id=creada.id,
            nombre=creada.nombre,
            genero=creada.genero,
            horas_mes=creada.horas_mes,
            horas_ano=creada.horas_ano,
            is_active=creada.is_active,
            cuad_lun_man_min=10,
            cuad_lun_tar_min=11,
            cuad_mar_man_min=12,
            cuad_mar_tar_min=13,
            cuad_mie_man_min=14,
            cuad_mie_tar_min=15,
            cuad_jue_man_min=16,
            cuad_jue_tar_min=17,
            cuad_vie_man_min=18,
            cuad_vie_tar_min=19,
            cuad_sab_man_min=20,
            cuad_sab_tar_min=21,
            cuad_dom_man_min=22,
            cuad_dom_tar_min=23,
            cuadrante_uniforme=False,
            trabaja_finde=True,
        )
        actualizada = self.use_cases.editar_persona(editada)
        self.assertFalse(actualizada.cuadrante_uniforme)
        self.assertEqual(actualizada.cuad_lun_man_min, 10)
        self.assertEqual(actualizada.cuad_mar_man_min, 12)
        self.assertEqual(actualizada.cuad_mie_man_min, 14)
        self.assertEqual(actualizada.cuad_jue_man_min, 16)
        self.assertEqual(actualizada.cuad_vie_man_min, 18)


    def test_editar_persona_sin_finde_conserva_cuadrantes_previos(self) -> None:
        creada = self.use_cases.crear_persona(_build_persona())
        editada = PersonaDTO(
            id=creada.id,
            nombre=creada.nombre,
            genero=creada.genero,
            horas_mes=creada.horas_mes,
            horas_ano=creada.horas_ano,
            is_active=creada.is_active,
            cuad_lun_man_min=creada.cuad_lun_man_min,
            cuad_lun_tar_min=creada.cuad_lun_tar_min,
            cuad_mar_man_min=creada.cuad_mar_man_min,
            cuad_mar_tar_min=creada.cuad_mar_tar_min,
            cuad_mie_man_min=creada.cuad_mie_man_min,
            cuad_mie_tar_min=creada.cuad_mie_tar_min,
            cuad_jue_man_min=creada.cuad_jue_man_min,
            cuad_jue_tar_min=creada.cuad_jue_tar_min,
            cuad_vie_man_min=creada.cuad_vie_man_min,
            cuad_vie_tar_min=creada.cuad_vie_tar_min,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
            cuadrante_uniforme=creada.cuadrante_uniforme,
            trabaja_finde=False,
        )

        actualizada = self.use_cases.editar_persona(editada)

        self.assertFalse(actualizada.trabaja_finde)
        self.assertEqual(actualizada.cuad_sab_man_min, creada.cuad_sab_man_min)
        self.assertEqual(actualizada.cuad_sab_tar_min, creada.cuad_sab_tar_min)
        self.assertEqual(actualizada.cuad_dom_man_min, creada.cuad_dom_man_min)
        self.assertEqual(actualizada.cuad_dom_tar_min, creada.cuad_dom_tar_min)

    def test_solicitud_completa_en_finde_sin_trabaja_finde_falla(self) -> None:
        creada = self.use_cases.crear_persona(
            PersonaDTO(
                id=None,
                nombre="Delegada Sin Finde",
                genero="F",
                horas_mes=0,
                horas_ano=0,
                is_active=True,
                cuad_lun_man_min=60,
                cuad_lun_tar_min=60,
                cuad_mar_man_min=60,
                cuad_mar_tar_min=60,
                cuad_mie_man_min=60,
                cuad_mie_tar_min=60,
                cuad_jue_man_min=60,
                cuad_jue_tar_min=60,
                cuad_vie_man_min=60,
                cuad_vie_tar_min=60,
                cuad_sab_man_min=120,
                cuad_sab_tar_min=120,
                cuad_dom_man_min=120,
                cuad_dom_tar_min=120,
                cuadrante_uniforme=False,
                trabaja_finde=False,
            )
        )

        solicitudes_repo = SolicitudRepositorySQLite(self.connection)
        solicitudes_uc = SolicitudUseCases(solicitudes_repo, self.repo)

        with self.assertRaises(BusinessRuleError):
            solicitudes_uc.agregar_solicitud(
                SolicitudDTO(
                    id=None,
                    persona_id=creada.id or 0,
                    fecha_solicitud="2026-01-10",
                    fecha_pedida="2026-01-10",
                    desde=None,
                    hasta=None,
                    completo=True,
                    horas=0,
                    observaciones=None,
                    pdf_path=None,
                    pdf_hash=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
