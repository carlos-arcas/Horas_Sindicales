from __future__ import annotations

from app.application.dto import FilaReportePdf, ReportePdf, TotalesReportePdf
from app.pdf.pdf_builder import _build_table_data


def _reporte() -> ReportePdf:
    filas = [
        FilaReportePdf(
            nombre="Dª Ana",
            fecha="01/01/24",
            horario="09:00 - 10:00",
            horas_hhmm="01:00",
            minutos_totales_fila=60,
        ),
        FilaReportePdf(
            nombre="Dª Ana",
            fecha="02/01/24",
            horario="10:00 - 12:30",
            horas_hhmm="02:30",
            minutos_totales_fila=150,
        ),
    ]
    return ReportePdf(filas=filas, totales=TotalesReportePdf(total_horas_hhmm="03:30", total_minutos=210))


def test_pdf_incluye_fila_total_y_columna_minutos() -> None:
    data = _build_table_data(_reporte())
    assert data[0] == ["Nombre", "Fecha", "Horario", "Horas", "Total (min)"]
    assert data[-1] == ["TOTAL", "", "", "03:30", "210"]
