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
INTRO_TEXT = (
    "Conforme a lo dispuesto en el art.68 e) del Estatuto de los Trabajadores, aprobado por el "
    "Real Decreto Legislativo 1/1995 de 24 de marzo, dispense la ausencia al trabajo de los/as "
    "trabajadores/as que a continuación se relacionan, los cuales han de resolver asuntos relativos "
    "al ejercicio de sus funciones, representando al personal de su empresa."
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
    horas: str
    minutos_impresos: int


def construir_pdf_solicitudes(
    solicitudes: Iterable[SolicitudDTO],
    persona: Persona,
    destino: Path,
    intro_text: str | None = None,
    logo_path: str | None = None,
    include_hours_in_horario: bool | None = None,
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
    styles.add(
        ParagraphStyle(
            name="PdfTitle",
            parent=styles["Title"],
            alignment=1,
            fontName="Helvetica-Bold",
            fontSize=14,
        )
    )

    _ = include_hours_in_horario
    rows = _build_rows(solicitudes_list, persona)
    data = _build_table_data(rows)

    table = Table(data, repeatRows=1, colWidths=[6.5 * cm, 3.5 * cm, 5 * cm, 3 * cm])
    total_row_index = len(data) - 1
    table_style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
    ]
    if len(data) > 2:
        table_style_commands.append(
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")])
        )

    table_style_commands.extend(
        [
            ("SPAN", (0, total_row_index), (2, total_row_index)),
            ("ALIGN", (0, total_row_index), (2, total_row_index), "RIGHT"),
            ("FONTNAME", (0, total_row_index), (3, total_row_index), "Helvetica-Bold"),
            ("BACKGROUND", (0, total_row_index), (3, total_row_index), colors.whitesmoke),
            ("LINEABOVE", (0, total_row_index), (3, total_row_index), 1.25, colors.black),
        ]
    )

    table.setStyle(TableStyle(table_style_commands))

    intro = intro_text if intro_text is not None else INTRO_TEXT
    story = [
        Spacer(1, 1.7 * cm),
        Paragraph("AUSENCIA DE CARGOS SINDICALES", styles["PdfTitle"]),
        Spacer(1, 1.1 * cm),
        Paragraph(intro, styles["Body"]),
        Spacer(1, 1.7 * cm),
        table,
    ]

    def on_page(canvas, _doc):
        _draw_header(canvas, _doc, header_height, logo_path)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return destino


def construir_pdf_historico(
    solicitudes: Iterable[SolicitudDTO],
    persona: Persona,
    destino: Path,
    intro_text: str | None = None,
    logo_path: str | None = None,
) -> Path:
    return construir_pdf_solicitudes(
        solicitudes,
        persona,
        destino,
        intro_text=intro_text,
        logo_path=logo_path,
        include_hours_in_horario=False,
    )


def build_nombre_archivo(nombre_solicitante: str, fechas: Iterable[str]) -> str:
    fechas_list = sorted({datetime.strptime(fecha, "%Y-%m-%d") for fecha in fechas})
    dias_texto = _format_dias_seleccionados(fechas_list)
    nombre = _sanitize_filename(nombre_solicitante)
    return (
        "A_Coordinadora_Solicitud_Horas_Sindicales_"
        f"({nombre})_({dias_texto}).pdf"
    )


def _build_rows(
    solicitudes: list[SolicitudDTO], persona: Persona
) -> list[PdfRow]:
    nombre = _format_nombre(persona)
    rows: list[PdfRow] = []
    for solicitud in sorted(solicitudes, key=lambda item: item.fecha_pedida):
        fecha = _format_fecha_tabla(solicitud.fecha_pedida)
        horario = _format_horario(solicitud)
        minutos_impresos = _minutos_impresos(solicitud)
        horas = minutes_to_hhmm(minutos_impresos)
        rows.append(
            PdfRow(
                nombre=nombre,
                fecha=fecha,
                horario=horario,
                horas=horas,
                minutos_impresos=minutos_impresos,
            )
        )
    return rows


def _build_table_data(rows: list[PdfRow]) -> list[list[str]]:
    data = [["Nombre", "Fecha", "Horario", "Horas"]]
    data.extend([[row.nombre, row.fecha, row.horario, row.horas] for row in rows])
    total_minutos = sum(parse_hhmm_to_minutes(row.horas) for row in rows)
    data.append(["TOTAL", "", "", minutes_to_hhmm(total_minutos)])
    return data


def parse_hhmm_to_minutes(hhmm: str) -> int:
    cleaned = hhmm.strip()
    if not cleaned:
        return 0
    hours_text, minutes_text = cleaned.split(":", 1)
    return int(hours_text) * 60 + int(minutes_text)


def minutes_to_hhmm(total_minutes: int) -> str:
    if total_minutes <= 0:
        return "00:00"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _format_nombre(persona: Persona) -> str:
    prefijo = "Dª" if persona.genero.upper() == "F" else "D."
    return f"{prefijo} {persona.nombre}"


def _format_fecha_tabla(fecha: str) -> str:
    return datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%y")


def _format_horario(solicitud: SolicitudDTO) -> str:
    if solicitud.completo:
        return "COMPLETO"
    desde = solicitud.desde or "--:--"
    hasta = solicitud.hasta or "--:--"
    return f"{desde} - {hasta}"


def _format_horas(solicitud: SolicitudDTO) -> str:
    return minutes_to_hhmm(_minutos_impresos(solicitud))


def _minutos_impresos(solicitud: SolicitudDTO) -> int:
    minutos = int(round(solicitud.horas * 60))
    if minutos <= 0:
        return 0
    return minutos


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


def _draw_header(canvas, doc, header_height: float, logo_path: str | None) -> None:
    width, height = A4
    logo_path = _resolve_logo_path(logo_path)
    max_width = width - doc.leftMargin - doc.rightMargin
    if logo_path.exists():
        logo = ImageReader(str(logo_path))
        logo_width, logo_height = logo.getSize()
        scale = min(max_width / logo_width, header_height / logo_height)
        draw_width = logo_width * scale
        draw_height = logo_height * scale
        x = doc.leftMargin + (max_width - draw_width) / 2
        logo_y = height - doc.topMargin + (doc.topMargin - draw_height) / 2
        canvas.drawImage(logo, x, logo_y, width=draw_width, height=draw_height, mask="auto")


def _resolve_logo_path(logo_path: str | None) -> Path:
    if logo_path:
        path = Path(logo_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / logo_path
        if path.exists():
            return path
    return Path(__file__).resolve().parents[2] / "logo.png"
