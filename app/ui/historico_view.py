from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from PySide6.QtCore import QDate, QModelIndex, QRegularExpression, QSortFilterProxyModel, Qt

from app.application.dto import SolicitudDTO
from app.ui.models_qt import SolicitudesTableModel


@dataclass(frozen=True)
class EstadoHistorico:
    code: str
    label: str
    badge: str


ESTADOS_HISTORICO: dict[str, EstadoHistorico] = {
    "PENDIENTE": EstadoHistorico("PENDIENTE", "Pendiente", "🕒 Pendiente"),
    "CONFIRMADA": EstadoHistorico("CONFIRMADA", "Confirmada", "✅ Confirmada"),
}


class HistoricoStatusResolver:
    @staticmethod
    def resolve(solicitud: SolicitudDTO) -> EstadoHistorico:
        if solicitud.generated:
            return ESTADOS_HISTORICO["CONFIRMADA"]
        return ESTADOS_HISTORICO["PENDIENTE"]


class HistoricoFilterProxyModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._filter_regex = QRegularExpression()
        self._date_from: QDate | None = None
        self._date_to: QDate | None = None
        self._estado_code: str | None = None
        self._delegada_id: int | None = None
        self.setDynamicSortFilter(True)

    def set_search_text(self, text: str) -> None:
        escaped = QRegularExpression.escape(text.strip())
        pattern = escaped.replace(r"\ ", ".*")
        self._filter_regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
        self.invalidateFilter()

    def set_date_range(self, date_from: QDate | None, date_to: QDate | None) -> None:
        self._date_from = date_from
        self._date_to = date_to
        self.invalidateFilter()

    def set_estado_code(self, estado_code: str | None) -> None:
        self._estado_code = estado_code
        self.invalidateFilter()

    def set_delegada_id(self, delegada_id: int | None) -> None:
        self._delegada_id = delegada_id
        self.invalidateFilter()

    def _source_solicitud(self, source_row: int) -> SolicitudDTO | None:
        source_model = self.sourceModel()
        if not isinstance(source_model, SolicitudesTableModel):
            return None
        return source_model.solicitud_at(source_row)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        solicitud = self._source_solicitud(source_row)
        if solicitud is None:
            return False

        if self._estado_code:
            estado = HistoricoStatusResolver.resolve(solicitud)
            if estado.code != self._estado_code:
                return False

        if self._delegada_id is not None and solicitud.persona_id != self._delegada_id:
            return False

        if self._date_from or self._date_to:
            fecha = QDate.fromString(solicitud.fecha_pedida, "yyyy-MM-dd")
            if not fecha.isValid():
                return False
            if self._date_from and fecha < self._date_from:
                return False
            if self._date_to and fecha > self._date_to:
                return False

        if self._filter_regex.pattern():
            values = [
                solicitud.fecha_pedida,
                solicitud.desde or "",
                solicitud.hasta or "",
                solicitud.notas or "",
                solicitud.observaciones or "",
                HistoricoStatusResolver.resolve(solicitud).label,
            ]
            source_model = self.sourceModel()
            if isinstance(source_model, SolicitudesTableModel):
                person_name = source_model.persona_name_for_id(solicitud.persona_id)
                if person_name:
                    values.append(person_name)
                for column in range(source_model.columnCount()):
                    idx = source_model.index(source_row, column)
                    values.append(str(source_model.data(idx, Qt.DisplayRole) or ""))
            haystack = " ".join(values)
            if not self._filter_regex.match(haystack).hasMatch():
                return False

        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        source_model = self.sourceModel()
        if isinstance(source_model, SolicitudesTableModel) and left.column() == right.column() == 0:
            left_solicitud = source_model.solicitud_at(left.row())
            right_solicitud = source_model.solicitud_at(right.row())
            if left_solicitud and right_solicitud:
                left_dt = _parse_datetime(left_solicitud.fecha_pedida, left_solicitud.desde, left_solicitud.hasta)
                right_dt = _parse_datetime(right_solicitud.fecha_pedida, right_solicitud.desde, right_solicitud.hasta)
                return left_dt < right_dt
        return super().lessThan(left, right)


class HistoricalViewModel:
    def __init__(self, solicitudes: Iterable[SolicitudDTO] | None = None) -> None:
        self.source_model = SolicitudesTableModel(list(solicitudes or []), show_estado=True)
        self.proxy_model = HistoricoFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)

    def set_solicitudes(self, solicitudes: list[SolicitudDTO]) -> None:
        self.source_model.set_solicitudes(solicitudes)

    def set_persona_nombres(self, persona_nombres: dict[int, str]) -> None:
        self.source_model.set_persona_nombres(persona_nombres)


def _parse_datetime(fecha: str, desde: str | None, hasta: str | None) -> datetime:
    time_text = desde or hasta or "00:00"
    try:
        return datetime.strptime(f"{fecha} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        return datetime.min
