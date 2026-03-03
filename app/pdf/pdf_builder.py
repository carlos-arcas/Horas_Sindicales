from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.application.dto import ReportePdf, SolicitudDTO
from app.application.use_cases.solicitudes.mapping_service import construir_reporte_pdf, construir_reporte_pdf_historico
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
    _validate_destino(destino)
    reporte = construir_reporte_pdf(solicitudes_list, nombre_persona=persona.nombre, genero=persona.genero)
    return construir_pdf_desde_modelo(
        reporte=reporte,
        destino=destino,
        intro_text=intro_text,
        logo_path=logo_path,
        include_hours_in_horario=include_hours_in_horario,
    )


def construir_pdf_desde_modelo(
    reporte: ReportePdf,
    destino: Path,
    intro_text: str | None = None,
    logo_path: str | None = None,
    include_hours_in_horario: bool | None = None,
) -> Path:
    destino = _ensure_pdf_extension(destino)
    _validate_destino(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        topMargin=4.5 * cm,
        bottomMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
    )
    _ = include_hours_in_horario

    data = _build_table_data(reporte)
    table = Table(data, repeatRows=1, colWidths=[5.1 * cm, 2.8 * cm, 4.1 * cm, 2.2 * cm, 2.8 * cm])
    total_row_index = len(data) - 1
    table.setStyle(TableStyle(_build_table_style(total_row_index, len(data))))

    styles = _build_styles()
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
        _draw_header(canvas, _doc, 3.0 * cm, logo_path)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return destino


def construir_pdf_historico(
    solicitudes: Iterable[SolicitudDTO],
    persona: Persona,
    destino: Path,
    intro_text: str | None = None,
    logo_path: str | None = None,
    personas_por_id: dict[int, Persona] | None = None,
) -> Path:
    solicitudes_list = list(solicitudes)
    if personas_por_id:
        reporte = construir_reporte_pdf_historico(
            solicitudes=solicitudes_list,
            nombre_por_persona_id={persona_id: item.nombre for persona_id, item in personas_por_id.items()},
            genero_por_persona_id={persona_id: item.genero for persona_id, item in personas_por_id.items()},
            nombre_por_defecto=persona.nombre,
            genero_por_defecto=persona.genero,
        )
        return construir_pdf_desde_modelo(
            reporte=reporte,
            destino=destino,
            intro_text=intro_text,
            logo_path=logo_path,
            include_hours_in_horario=False,
        )
    return construir_pdf_solicitudes(
        solicitudes_list,
        persona,
        destino,
        intro_text=intro_text,
        logo_path=logo_path,
        include_hours_in_horario=False,
    )


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], leading=14, spaceAfter=12))
    styles.add(
        ParagraphStyle(name="PdfTitle", parent=styles["Title"], alignment=1, fontName="Helvetica-Bold", fontSize=14)
    )
    return styles


def _build_table_data(reporte: ReportePdf) -> list[list[str]]:
    data = [["Nombre", "Fecha", "Horario", "Horas", "Total (min)"]]
    for fila in reporte.filas:
        data.append([fila.nombre, fila.fecha, fila.horario, fila.horas_hhmm, str(fila.minutos_totales_fila)])
    data.append(["TOTAL", "", "", reporte.totales.total_horas_hhmm, str(reporte.totales.total_minutos)])
    return data


def _build_table_style(total_row_index: int, total_rows: int) -> list[tuple]:
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("SPAN", (0, total_row_index), (2, total_row_index)),
        ("ALIGN", (0, total_row_index), (2, total_row_index), "RIGHT"),
        ("FONTNAME", (0, total_row_index), (4, total_row_index), "Helvetica-Bold"),
        ("BACKGROUND", (0, total_row_index), (4, total_row_index), colors.whitesmoke),
        ("LINEABOVE", (0, total_row_index), (4, total_row_index), 1.25, colors.black),
    ]
    if total_rows > 2:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]))
    return commands


def build_nombre_archivo(nombre_solicitante: str, fechas: Iterable[str]) -> str:
    fechas_list = sorted({datetime.strptime(fecha, "%Y-%m-%d") for fecha in fechas})
    dias_texto = _format_dias_seleccionados(fechas_list)
    nombre = _sanitize_filename(nombre_solicitante)
    return f"A_Coordinadora_Solicitud_Horas_Sindicales_({nombre})_({dias_texto}).pdf"


def _format_dias_seleccionados(fechas: list[datetime]) -> str:
    if not fechas:
        return "VARIOS"
    month_years = {(fecha.month, fecha.year) for fecha in fechas}
    if len(month_years) == 1:
        fecha_base = fechas[0]
        dias = [f"{fecha.day:02d}" for fecha in fechas]
        dias_texto = dias[0] if len(dias) == 1 else ", ".join(dias[:-1]) + f" y {dias[-1]}"
        return f"{dias_texto} {MONTH_ABBR[fecha_base.month]} {fecha_base.year}"
    return ", ".join(_format_fecha_archivo(fecha) for fecha in fechas)


def _format_fecha_archivo(fecha: datetime) -> str:
    return f"{fecha.day:02d} {MONTH_ABBR[fecha.month]} {fecha.year}"


def _sanitize_filename(nombre: str) -> str:
    normalized = unicodedata.normalize("NFKC", nombre or "")
    without_controls = "".join(char for char in normalized if unicodedata.category(char) not in {"Cc", "Cf"})
    without_separators = without_controls.replace("/", "-").replace("\\", "-")
    cleaned = re.sub(r'[<>:"|?*]', "", without_separators).strip().rstrip(" .")
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned).strip("._-")
    if not cleaned or not any(char.isalnum() for char in cleaned):
        return "SIN_NOMBRE"
    return cleaned[:80]


def _validate_destino(destino: Path) -> None:
    destination_text = destino.as_posix()
    if any(part == ".." for part in destino.parts):
        raise ValueError("La ruta de destino no puede contener '..'.")
    if _contains_path_separators(destino.name) or ".." in destino.name:
        raise ValueError("El destino debe ser un nombre de archivo PDF válido.")
    if destino.name != destination_text.split("/")[-1]:
        raise ValueError("El destino debe ser un nombre de archivo puro, sin rutas.")


def _ensure_pdf_extension(path: Path) -> Path:
    return path if path.suffix.lower() == ".pdf" else path.with_suffix(".pdf")


def _contains_path_separators(value: str) -> bool:
    return "/" in value or "\\" in value


def _draw_header(canvas, doc, header_height: float, logo_path: str | None) -> None:
    width, height = A4
    logo = _resolve_logo_path(logo_path)
    if not logo.exists():
        return
    max_width = width - doc.leftMargin - doc.rightMargin
    image = ImageReader(str(logo))
    logo_width, logo_height = image.getSize()
    scale = min(max_width / logo_width, header_height / logo_height)
    draw_width = logo_width * scale
    draw_height = logo_height * scale
    x = doc.leftMargin + (max_width - draw_width) / 2
    y = height - doc.topMargin + (doc.topMargin - draw_height) / 2
    canvas.drawImage(image, x, y, width=draw_width, height=draw_height, mask="auto")


def _resolve_logo_path(logo_path: str | None) -> Path:
    if logo_path:
        path = Path(logo_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / logo_path
        if path.exists():
            return path
    return Path(__file__).resolve().parents[2] / "logo.png"
