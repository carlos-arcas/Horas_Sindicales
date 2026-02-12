from __future__ import annotations

from app.pdf.pdf_builder import PdfRow, _build_table_data


def test_pdf_incluye_fila_total_y_columna_horas() -> None:
    rows = [
        PdfRow(nombre="Dª Ana", fecha="01/01/24", horario="09:00 - 10:00", horas="01:00", minutos_impresos=60),
        PdfRow(nombre="Dª Ana", fecha="02/01/24", horario="10:00 - 12:30", horas="02:30", minutos_impresos=150),
    ]

    data = _build_table_data(rows)

    assert data[0][3] == "Horas"
    assert data[-1] == ["TOTAL", "", "", "03:30"]
