from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph,
)

from app.application.dto import SolicitudDTO
from app.domain.models import Persona
from app.domain.time_utils import minutes_to_hhmm

INTRO_TEXT = (
    "Mediante el presente escrito se solicita autorización para la ausencia del puesto de trabajo "
    "con motivo del desempeño de cargos sindicales, de acuerdo con la normativa vigente."
)

MONTH_ABBR = {
    1: "ENE",
    2: "FEB",
    3: "MAR",
    4: "ABR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DIC",
}


@dataclass(frozen=True)
class PdfRow:
    nombre: str
    fecha: str
    horario: str


def construir_pdf_solicitudes(
    solicitudes: Iterable[SolicitudDTO], persona: Persona, destino: Path
) -> Path:
    solicitudes_list = list(solicitudes)
    if not solicitudes_list:
        raise ValueError("No hay solicitudes para generar el PDF.")

    destino = _ensure_pdf_extension(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    header_height = 3.0 * cm
    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        topMargin=4.5 * cm,
        bottomMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            leading=14,
            spaceAfter=12,
        )
    )

    rows = _build_rows(solicitudes_list, persona)
    data = [["Nombre", "Fecha", "Horario"]]
    data.extend([[row.nombre, row.fecha, row.horario] for row in rows])

    table = Table(data, repeatRows=1, colWidths=[7 * cm, 4 * cm, 5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ]
        )
    )

    story = [Paragraph(INTRO_TEXT, styles["Body"]), Spacer(1, 0.4 * cm), table]

    def on_page(canvas, _doc):
        _draw_header(canvas, _doc, header_height)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return destino


def build_nombre_archivo(nombre_solicitante: str, fechas: Iterable[str]) -> str:
    fechas_list = sorted({datetime.strptime(fecha, "%Y-%m-%d") for fecha in fechas})
    dias_texto = _format_dias_seleccionados(fechas_list)
    nombre = _sanitize_filename(nombre_solicitante)
    return (
        "A_Coordinadora_Solicitud_Horas_Sindicales_"
        f"({nombre})_({dias_texto}).pdf"
    )


def _build_rows(solicitudes: list[SolicitudDTO], persona: Persona) -> list[PdfRow]:
    nombre = _format_nombre(persona)
    rows: list[PdfRow] = []
    for solicitud in sorted(solicitudes, key=lambda item: item.fecha_pedida):
        fecha = _format_fecha_tabla(solicitud.fecha_pedida)
        horario = _format_horario(solicitud)
        rows.append(PdfRow(nombre=nombre, fecha=fecha, horario=horario))
    return rows


def _format_nombre(persona: Persona) -> str:
    prefijo = "Dª" if persona.genero.upper() == "F" else "D."
    return f"{prefijo} {persona.nombre}"


def _format_fecha_tabla(fecha: str) -> str:
    return datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")


def _format_horario(solicitud: SolicitudDTO) -> str:
    minutos = int(round(solicitud.horas * 60))
    if solicitud.completo:
        detalle = f" ({minutes_to_hhmm(minutos)})" if minutos > 0 else ""
        return f"COMPLETO{detalle}"
    desde = solicitud.desde or "--:--"
    hasta = solicitud.hasta or "--:--"
    return f"{desde} - {hasta}"


def _format_dias_seleccionados(fechas: list[datetime]) -> str:
    if not fechas:
        return "VARIOS"
    month_years = {(fecha.month, fecha.year) for fecha in fechas}
    if len(month_years) == 1:
        fecha_base = fechas[0]
        dias = [f"{fecha.day:02d}" for fecha in fechas]
        if len(dias) == 1:
            dias_texto = dias[0]
        else:
            dias_texto = ", ".join(dias[:-1]) + f" y {dias[-1]}"
        month = MONTH_ABBR[fecha_base.month]
        return f"{dias_texto} {month} {fecha_base.year}"

    return ", ".join(_format_fecha_archivo(fecha) for fecha in fechas)


def _format_fecha_archivo(fecha: datetime) -> str:
    month = MONTH_ABBR[fecha.month]
    return f"{fecha.day:02d} {month} {fecha.year}"


def _sanitize_filename(nombre: str) -> str:
    reemplazos = {"/": "-", "\\": "-", " ": "_"}
    for origen, destino in reemplazos.items():
        nombre = nombre.replace(origen, destino)
    return nombre


def _ensure_pdf_extension(path: Path) -> Path:
    if path.suffix.lower() != ".pdf":
        return path.with_suffix(".pdf")
    return path


def _draw_header(canvas, doc, header_height: float) -> None:
    width, height = A4
    logo_path = Path(__file__).resolve().parents[2] / "logo.png"
    max_width = width - doc.leftMargin - doc.rightMargin
    logo_y = height - doc.topMargin + (doc.topMargin - header_height) / 2
    if logo_path.exists():
        logo = ImageReader(str(logo_path))
        logo_width, logo_height = logo.getSize()
        scale = min(max_width / logo_width, header_height / logo_height)
        draw_width = logo_width * scale
        draw_height = logo_height * scale
        x = doc.leftMargin + (max_width - draw_width) / 2
        logo_y = height - doc.topMargin + (doc.topMargin - draw_height) / 2
        canvas.drawImage(logo, x, logo_y, width=draw_width, height=draw_height, mask="auto")
        title_y = logo_y - 0.4 * cm
    else:
        title_y = height - doc.topMargin + 0.2 * cm
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawCentredString(width / 2, title_y, "AUSENCIA DE CARGOS SINDICALES")
