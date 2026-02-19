from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Persona
from app.pdf.pdf_builder import (
    _build_rows,
    _build_table_data,
    _format_horario,
    _minutos_impresos,
    build_nombre_archivo,
    minutes_to_hhmm,
    parse_hhmm_to_minutes,
)


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


def _solicitud(fecha_pedida: str, horas: float, *, completo: bool = False, desde: str | None = "09:00", hasta: str | None = "10:00") -> SolicitudDTO:
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


def test_parse_hhmm_to_minutes_handles_empty_and_spaces() -> None:
    assert parse_hhmm_to_minutes("   ") == 0
    assert parse_hhmm_to_minutes(" 01:05 ") == 65


def test_minutes_to_hhmm_handles_zero_negative_and_conversion() -> None:
    assert minutes_to_hhmm(0) == "00:00"
    assert minutes_to_hhmm(-10) == "00:00"
    assert minutes_to_hhmm(61) == "01:01"


def test_minutos_impresos_rounds_and_limits_non_positive() -> None:
    assert _minutos_impresos(_solicitud("2025-01-01", 1.26)) == 76
    assert _minutos_impresos(_solicitud("2025-01-01", -0.2)) == 0


def test_format_horario_handles_completo_and_none_values() -> None:
    assert _format_horario(_solicitud("2025-01-01", 1.0, completo=True)) == "COMPLETO"
    assert _format_horario(_solicitud("2025-01-01", 1.0, desde=None, hasta=None)) == "--:-- - --:--"


def test_build_rows_sorts_by_date_and_formats_fields() -> None:
    persona = _persona("M")
    rows = _build_rows(
        [
            _solicitud("2025-01-20", 1.5, desde="10:00", hasta="11:30"),
            _solicitud("2025-01-05", 2.0, completo=True),
        ],
        persona,
    )

    assert [row.fecha for row in rows] == ["05/01/25", "20/01/25"]
    assert rows[0].nombre == "D. Ana / López"
    assert rows[0].horario == "COMPLETO"
    assert rows[1].horas == "01:30"


def test_build_table_data_includes_header_and_total_for_empty_rows() -> None:
    data = _build_table_data([])
    assert data[0] == ["Nombre", "Fecha", "Horario", "Horas"]
    assert data[-1] == ["TOTAL", "", "", "00:00"]


def test_build_nombre_archivo_sanitizes_and_formats_multiple_days_same_month() -> None:
    nombre = build_nombre_archivo("Ana/Lopez", ["2025-05-03", "2025-05-01", "2025-05-03"])
    assert nombre == "A_Coordinadora_Solicitud_Horas_Sindicales_(Ana-Lopez)_(01 y 03 MAY 2025).pdf"


def test_build_nombre_archivo_joins_dates_for_different_months() -> None:
    nombre = build_nombre_archivo("Ana Lopez", ["2025-05-31", "2025-06-01"])
    assert nombre == "A_Coordinadora_Solicitud_Horas_Sindicales_(Ana_Lopez)_(31 MAY 2025, 01 JUN 2025).pdf"
