from __future__ import annotations

import sqlite3
import unittest

from app.application.dto import PeriodoFiltro, SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


class SolicitudesHistoricoRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        run_migrations(self.connection)
        self.persona_repo = PersonaRepositorySQLite(self.connection)
        self.solicitud_repo = SolicitudRepositorySQLite(self.connection)
        self.use_cases = SolicitudUseCases(self.solicitud_repo, self.persona_repo)
        persona = self.persona_repo.create(
            Persona(
                id=None,
                nombre="Delegada Test",
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
            )
        )
        self.persona_id = persona.id or 0

    def tearDown(self) -> None:
        self.connection.close()

    def _build_solicitud(self, fecha: str = "2025-01-15") -> SolicitudDTO:
        return SolicitudDTO(
            id=None,
            persona_id=self.persona_id,
            fecha_solicitud="2025-01-01",
            fecha_pedida=fecha,
            desde="09:00",
            hasta="11:00",
            completo=False,
            horas=2.0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
        )

    def test_peticion_pendiente_no_modifica_total_historico(self) -> None:
        self.use_cases.agregar_solicitud(self._build_solicitud())

        resumen = self.use_cases.calcular_resumen_saldos(self.persona_id, PeriodoFiltro.mensual(2025, 1))

        self.assertEqual(resumen.individual.consumidas_periodo_min, 0)
        self.assertEqual(resumen.individual.consumidas_anual_min, 0)

    def test_generar_y_pasar_a_historico_incrementa_total(self) -> None:
        creada, _ = self.use_cases.agregar_solicitud(self._build_solicitud())
        assert creada.id is not None
        self.solicitud_repo.update_pdf_info(creada.id, "/tmp/test.pdf", "hash")

        resumen = self.use_cases.calcular_resumen_saldos(self.persona_id, PeriodoFiltro.mensual(2025, 1))

        self.assertEqual(resumen.individual.consumidas_periodo_min, 120)
        self.assertEqual(resumen.individual.consumidas_anual_min, 120)

    def test_insertar_y_borrar_peticion_pendiente_no_duplica_ni_cambia_total(self) -> None:
        creada, _ = self.use_cases.agregar_solicitud(self._build_solicitud())
        assert creada.id is not None
        self.use_cases.eliminar_solicitud(creada.id)

        resumen = self.use_cases.calcular_resumen_saldos(self.persona_id, PeriodoFiltro.mensual(2025, 1))

        self.assertEqual(resumen.individual.consumidas_periodo_min, 0)
        self.assertEqual(resumen.individual.consumidas_anual_min, 0)

    def test_listar_solicitudes_por_persona_devuelve_todas_sin_filtrar_periodo(self) -> None:
        primera, _ = self.use_cases.agregar_solicitud(self._build_solicitud("2025-01-15"))
        segunda, _ = self.use_cases.agregar_solicitud(self._build_solicitud("2025-02-10"))
        assert primera.id is not None and segunda.id is not None
        self.solicitud_repo.update_pdf_info(primera.id, "/tmp/test1.pdf", "hash1")
        self.solicitud_repo.update_pdf_info(segunda.id, "/tmp/test2.pdf", "hash2")

        solicitudes = list(self.use_cases.listar_solicitudes_por_persona(self.persona_id))

        self.assertEqual(len(solicitudes), 2)

    def test_no_hay_doble_sumatorio_tras_insert_delete_insert_y_generar(self) -> None:
        primera, _ = self.use_cases.agregar_solicitud(self._build_solicitud("2025-01-15"))
        assert primera.id is not None
        self.use_cases.eliminar_solicitud(primera.id)

        segunda, _ = self.use_cases.agregar_solicitud(self._build_solicitud("2025-01-16"))
        assert segunda.id is not None
        self.solicitud_repo.update_pdf_info(segunda.id, "/tmp/test2.pdf", "hash2")

        resumen = self.use_cases.calcular_resumen_saldos(self.persona_id, PeriodoFiltro.mensual(2025, 1))

        self.assertEqual(resumen.individual.consumidas_periodo_min, 120)
        self.assertEqual(resumen.individual.consumidas_anual_min, 120)


if __name__ == "__main__":
    unittest.main()
