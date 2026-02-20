from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.domain.models import Persona
from app.infrastructure.pdf.generador_pdf_reportlab import GeneradorPdfReportlab


def test_generador_pdf_reportlab_smoke(tmp_path: Path) -> None:
    adapter = GeneradorPdfReportlab()
    persona = Persona(
        id=1,
        nombre="Delegada Smoke",
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
    solicitudes = [
        SolicitudDTO(
            id=1,
            persona_id=1,
            fecha_solicitud="2025-01-10",
            fecha_pedida="2025-01-15",
            desde="09:00",
            hasta="11:00",
            completo=False,
            horas=2.0,
            observaciones="",
            pdf_path=None,
            pdf_hash=None,
            notas="",
        )
    ]

    destino = tmp_path / "smoke.pdf"
    generado = adapter.generar_pdf_solicitudes(solicitudes, persona, destino)

    assert generado.exists()
    assert generado.stat().st_size > 0
