import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.application.dto import FilaReportePdf, ReportePdf, TotalesReportePdf
from app.pdf.pdf_builder import _build_table_data


def test_build_table_data_adds_total_row_hhmm_and_minutos() -> None:
    reporte = ReportePdf(
        filas=[
            FilaReportePdf(
                nombre="Dª Ana",
                fecha="01/01/24",
                horario="09:00 - 11:30",
                horas_hhmm="02:30",
                minutos_totales_fila=150,
            ),
            FilaReportePdf(
                nombre="Dª Ana",
                fecha="02/01/24",
                horario="COMPLETO",
                horas_hhmm="01:45",
                minutos_totales_fila=105,
            ),
        ],
        totales=TotalesReportePdf(total_horas_hhmm="04:15", total_minutos=255),
    )

    data = _build_table_data(reporte)

    assert data[-1] == ["TOTAL", "", "", "04:15", "255"]
