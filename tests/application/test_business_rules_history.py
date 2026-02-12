from __future__ import annotations

from app.application.dto import PeriodoFiltro


def test_no_contar_pendientes_hasta_historico(solicitud_use_cases, solicitud_repo, solicitud_dto, persona_id) -> None:
    creada, _ = solicitud_use_cases.agregar_solicitud(solicitud_dto)
    assert creada.id is not None

    resumen_pendiente = solicitud_use_cases.calcular_resumen_saldos(persona_id, PeriodoFiltro.mensual(2025, 1))
    assert resumen_pendiente.individual.consumidas_periodo_min == 0

    solicitud_repo.update_pdf_info(creada.id, "/tmp/historico.pdf", "hash-historico")

    resumen_historico = solicitud_use_cases.calcular_resumen_saldos(persona_id, PeriodoFiltro.mensual(2025, 1))
    assert resumen_historico.individual.consumidas_periodo_min == 120
