import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pdf.pdf_builder import (
    PdfRow,
    _build_table_data,
    minutes_to_hhmm,
    parse_hhmm_to_minutes,
)


def test_build_table_data_adds_total_row_in_hhmm() -> None:
    rows = [
        PdfRow(
            nombre="Dª Ana",
            fecha="01/01/24",
            horario="09:00 - 11:30",
            horas="02:30",
            minutos_impresos=150,
        ),
        PdfRow(
            nombre="Dª Ana",
            fecha="02/01/24",
            horario="COMPLETO",
            horas="01:45",
            minutos_impresos=105,
        ),
    ]

    data = _build_table_data(rows)

    assert data[-1] == ["TOTAL", "", "", "04:15"]


def test_hhmm_helpers_round_trip() -> None:
    assert parse_hhmm_to_minutes("04:15") == 255
    assert minutes_to_hhmm(255) == "04:15"
