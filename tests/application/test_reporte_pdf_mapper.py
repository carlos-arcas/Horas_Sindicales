from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.mapping_service import construir_reporte_pdf, construir_reporte_pdf_historico
from app.domain.models import Persona


def _persona() -> Persona:
    return Persona(
        id=99,
        nombre="Delegada Demo",
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


def _solicitud(fecha: str, horas: float) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=99,
        fecha_solicitud="2025-01-01",
        fecha_pedida=fecha,
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=horas,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_mapper_puebla_minutos_totales_por_fila_y_total_global() -> None:
    reporte = construir_reporte_pdf(
        [
            _solicitud("2025-01-02", 1.5),
            _solicitud("2025-01-01", 0.51),
        ],
        nombre_persona=_persona().nombre,
        genero=_persona().genero,
    )

    assert [fila.minutos_totales_fila for fila in reporte.filas] == [31, 90]
    assert reporte.totales.total_minutos == 121
    assert reporte.totales.total_horas_hhmm == "02:01"


def test_mapper_historico_resuelve_nombre_por_persona_id_en_cada_fila() -> None:
    solicitudes = [
        SolicitudDTO(
            id=1,
            persona_id=1,
            fecha_solicitud="2025-02-01",
            fecha_pedida="2025-02-01",
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
        ),
        SolicitudDTO(
            id=2,
            persona_id=2,
            fecha_solicitud="2025-02-02",
            fecha_pedida="2025-02-02",
            desde="11:00",
            hasta="12:00",
            completo=False,
            horas=1.0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
        ),
    ]

    reporte = construir_reporte_pdf_historico(
        solicitudes=solicitudes,
        nombre_por_persona_id={1: "Dora Delegada", 2: "Lorena Delegada"},
        genero_por_persona_id={1: "F", 2: "F"},
        nombre_por_defecto="Delegada Fallback",
        genero_por_defecto="F",
    )

    assert [fila.nombre for fila in reporte.filas] == ["Dª Dora Delegada", "Dª Lorena Delegada"]
