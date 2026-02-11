import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pdf.pdf_builder import PdfRow, _build_table_data


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

    assert data[-1] == ["", "", "TOTAL:", "04:15"]
