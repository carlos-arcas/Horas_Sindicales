from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from app.application.dto import PersonaDTO, SolicitudDTO
from app.domain.time_utils import minutes_to_hhmm
from app.ui.patterns import status_badge


SOLICITUD_FECHA_ROLE = Qt.UserRole + 1


def _format_minutes(minutes: int) -> str:
    if minutes < 0:
        minutes = abs(minutes)
        return f"-{minutes_to_hhmm(minutes)}"
    return minutes_to_hhmm(minutes)


class PersonasTableModel(QAbstractTableModel):
    def __init__(self, personas: list[PersonaDTO] | None = None) -> None:
        super().__init__()
        self._personas = personas or []
        self._headers = [
            "Nombre",
            "Género",
            "Horas mes",
            "Horas año",
        ]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._personas)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        persona = self._personas[index.row()]
        column = index.column()
        if column == 0:
            return persona.nombre
        if column == 1:
            return persona.genero
        if column == 2:
            return _format_minutes(persona.horas_mes)
        if column == 3:
            return _format_minutes(persona.horas_ano)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return str(section + 1)

    def set_personas(self, personas: list[PersonaDTO]) -> None:
        self.beginResetModel()
        self._personas = personas
        self.endResetModel()

    def persona_at(self, row: int) -> PersonaDTO | None:
        if 0 <= row < len(self._personas):
            return self._personas[row]
        return None


class SolicitudesTableModel(QAbstractTableModel):
    def __init__(
        self,
        solicitudes: list[SolicitudDTO] | None = None,
        *,
        show_estado: bool = False,
    ) -> None:
        super().__init__()
        self._solicitudes = solicitudes or []
        self._headers = [
            "Fecha pedida",
            "Desde",
            "Hasta",
            "Completo",
            "Horas",
            "Notas",
        ]
        self._show_delegada = False
        self._show_estado = show_estado
        self._persona_nombres: dict[int, str] = {}
        self._conflict_rows: set[int] = set()
        self._fecha_pedida_dates: list[date | None] = [self._parse_fecha_pedida(sol.fecha_pedida) for sol in self._solicitudes]

    def _effective_headers(self) -> list[str]:
        headers = list(self._headers)
        if self._show_estado:
            headers.append("Estado")
        if self._show_delegada:
            headers.append("Delegada")
        return headers

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._solicitudes)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._effective_headers())

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == SOLICITUD_FECHA_ROLE and index.column() == 0:
            return self._fecha_pedida_dates[index.row()]
        role_handlers = {
            Qt.DisplayRole: self._data_display,
            Qt.ToolTipRole: self._data_tooltip,
            Qt.ForegroundRole: self._data_foreground,
            Qt.FontRole: self._data_font,
        }
        handler = role_handlers.get(role)
        if handler is None:
            return None
        return handler(index)

    def _data_display(self, index: QModelIndex):
        solicitud = self._solicitudes[index.row()]
        column = index.column()
        if column == 0:
            return solicitud.fecha_pedida
        if column == 1:
            return solicitud.desde or "-"
        if column == 2:
            return solicitud.hasta or "-"
        if column == 3:
            return "Sí" if solicitud.completo else "No"
        if column == 4:
            return _format_minutes(int(round(solicitud.horas * 60)))
        if column == 5:
            return solicitud.notas or ""

        dynamic_column = 6
        if self._show_estado and column == dynamic_column:
            if solicitud.generated:
                return status_badge("CONFIRMED")
            return status_badge("PENDING")
        if self._show_estado:
            dynamic_column += 1

        if self._show_delegada and column == dynamic_column:
            return self._persona_nombres.get(solicitud.persona_id, "(sin delegada)")
        return None

    def _data_tooltip(self, index: QModelIndex):
        column = index.column()
        if column == 5:
            return self._solicitudes[index.row()].notas or ""
        if self._is_conflict_marker_column(index):
            return "⚠ Horario solapado con otra petición pendiente del mismo día."
        return None

    def _data_foreground(self, index: QModelIndex):
        if self._is_conflict_marker_column(index):
            return QColor("#c62828")
        return None

    def _data_font(self, index: QModelIndex):
        if not self._is_conflict_marker_column(index):
            return None
        font = QFont()
        font.setUnderline(True)
        return font

    def _is_conflict_marker_column(self, index: QModelIndex) -> bool:
        return index.row() in self._conflict_rows and index.column() == 0

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            headers = self._effective_headers()
            if 0 <= section < len(headers):
                return headers[section]
            return None
        return str(section + 1)

    def set_solicitudes(self, solicitudes: list[SolicitudDTO]) -> None:
        self.beginResetModel()
        self._solicitudes = solicitudes
        self._conflict_rows = set()
        self._fecha_pedida_dates = [self._parse_fecha_pedida(sol.fecha_pedida) for sol in self._solicitudes]
        self.endResetModel()

    def solicitud_at(self, row: int) -> SolicitudDTO | None:
        if 0 <= row < len(self._solicitudes):
            return self._solicitudes[row]
        return None

    def append_solicitud(self, solicitud: SolicitudDTO) -> None:
        row = len(self._solicitudes)
        self.beginInsertRows(QModelIndex(), row, row)
        self._solicitudes.append(solicitud)
        self._fecha_pedida_dates.append(self._parse_fecha_pedida(solicitud.fecha_pedida))
        self.endInsertRows()

    def solicitudes(self) -> list[SolicitudDTO]:
        return list(self._solicitudes)

    def clear(self) -> None:
        self.beginResetModel()
        self._solicitudes = []
        self._conflict_rows = set()
        self._fecha_pedida_dates = []
        self.endResetModel()

    def fecha_pedida_date_at(self, row: int) -> date | None:
        if 0 <= row < len(self._fecha_pedida_dates):
            return self._fecha_pedida_dates[row]
        return None

    @staticmethod
    def _parse_fecha_pedida(value: str) -> date | None:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def set_conflict_rows(self, rows: set[int]) -> None:
        self.beginResetModel()
        self._conflict_rows = set(rows)
        self.endResetModel()

    def set_show_delegada(self, show: bool) -> None:
        self.beginResetModel()
        self._show_delegada = show
        self.endResetModel()

    def persona_name_for_id(self, persona_id: int) -> str:
        return self._persona_nombres.get(persona_id, "")

    def set_persona_nombres(self, persona_nombres: dict[int, str]) -> None:
        self.beginResetModel()
        self._persona_nombres = dict(persona_nombres)
        self.endResetModel()
