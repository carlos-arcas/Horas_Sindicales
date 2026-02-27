from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from PySide6.QtCore import QDate, QModelIndex, QRegularExpression, QSortFilterProxyModel, Qt

from app.application.dto import SolicitudDTO
from app.ui.models_qt import SOLICITUD_FECHA_ROLE, SolicitudesTableModel
from app.ui.patterns import status_badge


@dataclass(frozen=True)
class EstadoHistorico:
    code: str
    label: str
    badge: str


ESTADOS_HISTORICO: dict[str, EstadoHistorico] = {
    "PENDIENTE": EstadoHistorico("PENDIENTE", "Pendiente", status_badge("PENDING")),
    "CONFIRMADA": EstadoHistorico("CONFIRMADA", "Confirmada", status_badge("CONFIRMED")),
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
        self._date_from_py: date | None = None
        self._date_to_py: date | None = None
        self._estado_code: str | None = None
        self._delegada_id: int | None = None
        self._ver_todas: bool = True
        self._year_mode: str = "RANGE"
        self._year: int | None = None
        self._month: int | None = None
        self.setDynamicSortFilter(True)

    def set_search_text(self, text: str) -> None:
        escaped = QRegularExpression.escape(text.strip())
        pattern = escaped.replace(r"\ ", ".*")
        self._filter_regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
        self.invalidateFilter()

    def set_date_range(self, date_from: QDate | None, date_to: QDate | None) -> None:
        self.set_filters(
            delegada_id=self._delegada_id,
            ver_todas=self._ver_todas,
            year_mode="RANGE",
            year=self._year,
            month=self._month,
            date_from=date_from,
            date_to=date_to,
        )

    def set_estado_code(self, estado_code: str | None) -> None:
        self._estado_code = estado_code
        self.invalidateFilter()

    def set_delegada_id(self, delegada_id: int | None) -> None:
        self._delegada_id = delegada_id
        self._ver_todas = delegada_id is None
        self.invalidateFilter()

    def set_filters(
        self,
        *,
        delegada_id: int | None,
        ver_todas: bool,
        year_mode: str,
        year: int | None,
        month: int | None,
        date_from: QDate | date | None,
        date_to: QDate | date | None,
    ) -> None:
        self._delegada_id = int(delegada_id) if delegada_id is not None else None
        self._ver_todas = bool(ver_todas)
        self._year_mode = year_mode or "RANGE"
        self._year = int(year) if year is not None else None
        self._month = int(month) if month is not None else None
        self._date_from_py = self._normalize_date(date_from)
        self._date_to_py = self._normalize_date(date_to)
        self._date_from = QDate(self._date_from_py.year, self._date_from_py.month, self._date_from_py.day) if self._date_from_py else None
        self._date_to = QDate(self._date_to_py.year, self._date_to_py.month, self._date_to_py.day) if self._date_to_py else None
        self.invalidateFilter()
        self.invalidate()

    def filter_state(self) -> dict[str, object]:
        return {
            "ver_todas": self._ver_todas,
            "delegada_id": self._delegada_id,
            "year_mode": self._year_mode,
            "year": self._year,
            "month": self._month,
            "from": self._date_from_py,
            "to": self._date_to_py,
        }

    def _source_solicitud(self, source_row: int) -> SolicitudDTO | None:
        source_model = self.sourceModel()
        if not isinstance(source_model, SolicitudesTableModel):
            return None
        return source_model.solicitud_at(source_row)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        solicitud = self._source_solicitud(source_row)
        if solicitud is None:
            return False

        has_period_filter = (
            (self._year_mode == "ALL_YEAR" and self._year is not None)
            or (self._year_mode == "YEAR_MONTH" and self._year is not None and self._month is not None)
            or (self._year_mode == "RANGE" and (self._date_from_py is not None or self._date_to_py is not None))
        )
        has_text_filter = bool(self._filter_regex.pattern())
        if not has_text_filter and not self._estado_code and not has_period_filter and (self._ver_todas or self._delegada_id is None):
            return True

        if self._estado_code:
            estado = HistoricoStatusResolver.resolve(solicitud)
            if estado.code != self._estado_code:
                return False

        if not self._ver_todas and self._delegada_id is not None and solicitud.persona_id != self._delegada_id:
            return False

        fecha = self._source_fecha(source_row)
        if self._year_mode == "ALL_YEAR" and self._year is not None:
            if fecha is None or fecha.year != self._year:
                return False
        elif self._year_mode == "YEAR_MONTH" and self._year is not None and self._month is not None:
            if fecha is None or fecha.year != self._year or fecha.month != self._month:
                return False
        elif self._year_mode == "RANGE" and (self._date_from_py or self._date_to_py):
            if fecha is None:
                return True
            from_date = self._normalize_date(self._date_from_py)
            to_date = self._normalize_date(self._date_to_py)
            if from_date and to_date and not (from_date <= fecha <= to_date):
                return False
            if from_date and fecha < from_date:
                return False
            if to_date and fecha > to_date:
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

    def _source_fecha(self, source_row: int) -> date | None:
        source_model = self.sourceModel()
        if isinstance(source_model, SolicitudesTableModel):
            idx = source_model.index(source_row, 0)
            fecha = source_model.data(idx, SOLICITUD_FECHA_ROLE)
            fecha_dt = self._normalize_date(fecha)
            if fecha_dt is not None:
                return fecha_dt
            return self._normalize_date(source_model.fecha_pedida_date_at(source_row))
        return None

    @staticmethod
    def _normalize_date(value: QDate | date | datetime | str | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            return None
        if isinstance(value, QDate) and value.isValid():
            return date(value.year(), value.month(), value.day())
        return None

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
