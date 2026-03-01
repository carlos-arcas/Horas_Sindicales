from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.mapping_service import construir_reporte_pdf
from app.domain.models import Persona
from app.pdf.pdf_builder import _build_table_data, build_nombre_archivo


def _persona(genero: str = "F") -> Persona:
    return Persona(
        id=1,
        nombre="Ana / López",
        genero=genero,
        horas_mes_min=600,
        horas_ano_min=7200,
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


def _solicitud(
    fecha_pedida: str,
    horas: float,
    *,
    completo: bool = False,
    desde: str | None = "09:00",
    hasta: str | None = "10:00",
) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida=fecha_pedida,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=horas,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_construir_reporte_pdf_arma_filas_ordenadas_y_minutos_totales() -> None:
    reporte = construir_reporte_pdf(
        [
            _solicitud("2025-01-20", 1.5, desde="10:00", hasta="11:30"),
            _solicitud("2025-01-05", 2.0, completo=True),
        ],
        nombre_persona=_persona("M").nombre,
        genero="M",
    )

    assert [fila.fecha for fila in reporte.filas] == ["05/01/25", "20/01/25"]
    assert reporte.filas[0].nombre == "D. Ana / López"
    assert reporte.filas[0].horario == "COMPLETO"
    assert reporte.filas[1].horas_hhmm == "01:30"
    assert reporte.filas[1].minutos_totales_fila == 90
    assert reporte.totales.total_minutos == 210


def test_build_table_data_includes_header_and_total_for_empty_rows() -> None:
    reporte = construir_reporte_pdf([], nombre_persona=_persona().nombre, genero=_persona().genero)
    data = _build_table_data(reporte)
    assert data[0] == ["Nombre", "Fecha", "Horario", "Horas", "Total (min)"]
    assert data[-1] == ["TOTAL", "", "", "00:00", "0"]


def test_build_nombre_archivo_sanitizes_and_formats_multiple_days_same_month() -> None:
    nombre = build_nombre_archivo("Ana/Lopez", ["2025-05-03", "2025-05-01", "2025-05-03"])
    assert nombre == "A_Coordinadora_Solicitud_Horas_Sindicales_(Ana-Lopez)_(01 y 03 MAY 2025).pdf"


def test_build_nombre_archivo_joins_dates_for_different_months() -> None:
    nombre = build_nombre_archivo("Ana Lopez", ["2025-05-31", "2025-06-01"])
    assert nombre == "A_Coordinadora_Solicitud_Horas_Sindicales_(Ana_Lopez)_(31 MAY 2025, 01 JUN 2025).pdf"
