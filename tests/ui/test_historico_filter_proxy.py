from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import importlib
import re
import sys
import types

import pytest

from app.application.dto import SolicitudDTO

pytestmark = pytest.mark.headless_safe


def _load_historico_components():
    try:
        from PySide6.QtCore import QDate, QModelIndex
        from app.ui.historico_view import HistoricoFilterProxyModel
        from app.ui.models_qt import SolicitudesTableModel

        return QDate, QModelIndex, HistoricoFilterProxyModel, SolicitudesTableModel
    except ImportError:
        # Fallback minimal para entornos sin PySide6.
        qtcore = types.ModuleType("PySide6.QtCore")

        class Qt:
            DisplayRole = 0
            UserRole = 1000

        class QModelIndex:
            def __init__(self, row: int = -1, column: int = -1):
                self._row = row
                self._column = column

            def row(self) -> int:
                return self._row

            def column(self) -> int:
                return self._column

            def isValid(self) -> bool:  # noqa: N802
                return self._row >= 0 and self._column >= 0

        class _RegexMatch:
            def __init__(self, ok: bool):
                self._ok = ok

            def hasMatch(self) -> bool:  # noqa: N802
                return self._ok

        class QRegularExpression:
            CaseInsensitiveOption = 1

            def __init__(self, pattern: str = "", options: int = 0):
                self._pattern = pattern
                self._flags = re.IGNORECASE if options == self.CaseInsensitiveOption else 0

            @staticmethod
            def escape(text: str) -> str:
                return re.escape(text)

            def pattern(self) -> str:
                return self._pattern

            def match(self, haystack: str) -> _RegexMatch:
                return _RegexMatch(re.search(self._pattern, haystack, flags=self._flags) is not None)

        class QDate:
            def __init__(self, year: int, month: int, day: int):
                self._year = year
                self._month = month
                self._day = day

            def isValid(self) -> bool:  # noqa: N802
                try:
                    date(self._year, self._month, self._day)
                except ValueError:
                    return False
                return True

            def year(self) -> int:
                return self._year

            def month(self) -> int:
                return self._month

            def day(self) -> int:
                return self._day

        class QSortFilterProxyModel:
            def __init__(self):
                self._source = None

            def setDynamicSortFilter(self, _enabled: bool) -> None:  # noqa: N802
                return None

            def setSourceModel(self, model) -> None:  # noqa: ANN001, N802
                self._source = model

            def sourceModel(self):  # noqa: ANN201, N802
                return self._source

            def invalidateFilter(self) -> None:
                return None

            def invalidate(self) -> None:
                return None

            def rowCount(self) -> int:  # noqa: N802
                if self._source is None:
                    return 0
                return sum(1 for row in range(self._source.rowCount()) if self.filterAcceptsRow(row, QModelIndex()))

            def index(self, row: int, column: int) -> QModelIndex:
                return QModelIndex(row, column)

            def lessThan(self, _left: QModelIndex, _right: QModelIndex) -> bool:  # noqa: N802
                return False

        qtcore.QDate = QDate
        qtcore.QModelIndex = QModelIndex
        qtcore.QRegularExpression = QRegularExpression
        qtcore.QSortFilterProxyModel = QSortFilterProxyModel
        qtcore.Qt = Qt

        pyside6 = types.ModuleType("PySide6")
        pyside6.QtCore = qtcore
        qtgui = types.ModuleType("PySide6.QtGui")
        qtwidgets = types.ModuleType("PySide6.QtWidgets")

        class _Dummy:
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
                return None

        qtgui.QKeySequence = _Dummy
        qtgui.QShortcut = _Dummy
        qtwidgets.QDialog = _Dummy
        qtwidgets.QHBoxLayout = _Dummy
        qtwidgets.QPushButton = _Dummy

        pyside6.QtGui = qtgui
        pyside6.QtWidgets = qtwidgets
        sys.modules["PySide6"] = pyside6
        sys.modules["PySide6.QtCore"] = qtcore
        sys.modules["PySide6.QtGui"] = qtgui
        sys.modules["PySide6.QtWidgets"] = qtwidgets

        models_qt = types.ModuleType("app.ui.models_qt")
        SOLICITUD_FECHA_ROLE = Qt.UserRole + 1

        class SolicitudesTableModel:
            def __init__(self, solicitudes):
                self._solicitudes = list(solicitudes)
                self._fecha_values = [self._parse_fecha(sol.fecha_pedida) for sol in self._solicitudes]
                self._persona_nombres: dict[int, str] = {}

            def rowCount(self) -> int:  # noqa: N802
                return len(self._solicitudes)

            def columnCount(self) -> int:  # noqa: N802
                return 6

            def index(self, row: int, column: int) -> QModelIndex:
                return QModelIndex(row, column)

            def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
                if role == SOLICITUD_FECHA_ROLE and index.column() == 0:
                    return self._fecha_values[index.row()]
                sol = self._solicitudes[index.row()]
                mapping = [sol.fecha_pedida, sol.desde or "-", sol.hasta or "-", "", "", sol.notas or ""]
                return mapping[index.column()] if 0 <= index.column() < len(mapping) else None

            def solicitud_at(self, row: int) -> SolicitudDTO | None:
                return self._solicitudes[row] if 0 <= row < len(self._solicitudes) else None

            def fecha_pedida_date_at(self, row: int) -> date | None:
                value = self._solicitudes[row].fecha_pedida
                return self._parse_fecha(value)

            def persona_name_for_id(self, persona_id: int) -> str:
                return self._persona_nombres.get(persona_id, "")

            @staticmethod
            def _parse_fecha(value: str) -> date | None:
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    return None

        models_qt.SOLICITUD_FECHA_ROLE = SOLICITUD_FECHA_ROLE
        models_qt.SolicitudesTableModel = SolicitudesTableModel
        sys.modules["app.ui.models_qt"] = models_qt

        hv = importlib.import_module("app.ui.historico_view")
        hv = importlib.reload(hv)
        return QDate, QModelIndex, hv.HistoricoFilterProxyModel, SolicitudesTableModel


QDate, QModelIndex, HistoricoFilterProxyModel, SolicitudesTableModel = _load_historico_components()


@dataclass(frozen=True)
class RowExpectation:
    row: int
    accepted: bool


def _solicitud(solicitud_id: int, fecha: str, persona_id: int, *, generated: bool = False, notas: str | None = "nota", observaciones: str | None = "obs", desde: str | None = "09:00", hasta: str | None = "10:00") -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=1.0,
        observaciones=observaciones,
        pdf_path=None,
        pdf_hash=None,
        notas=notas,
        generated=generated,
    )


def _build_source_model() -> SolicitudesTableModel:
    model = SolicitudesTableModel([
        _solicitud(1, "2026-01-10", 1, generated=False),
        _solicitud(2, "2026-01-20", 1, generated=True),
        _solicitud(3, "2026-02-15", 2, generated=False),
        _solicitud(4, "2025-12-31", 1, generated=False),
        _solicitud(5, "2026-03-01", 3, generated=True),
        _solicitud(6, "2026-02-15", 2, generated=False),
        _solicitud(7, "2026-02-17", 2, generated=False),
        _solicitud(8, "2026-02-28", 1, generated=False, notas=None, observaciones=None, desde=None, hasta=None),
        _solicitud(9, "", 3, generated=False, notas=None, observaciones=None, desde=None, hasta=None),
    ])

    # Forzamos ramas de fechas no ISO: válida d/m/Y, inválida y faltante.
    if hasattr(model, "_fecha_pedida_dates"):
        model._fecha_pedida_dates[5] = "15/02/2026"
        model._fecha_pedida_dates[6] = "fecha-invalida"
        model._fecha_pedida_dates[8] = None
    if hasattr(model, "_fecha_values"):
        model._fecha_values[5] = "15/02/2026"
        model._fecha_values[6] = "fecha-invalida"
        model._fecha_values[8] = None

    return model


def _build_proxy() -> HistoricoFilterProxyModel:
    proxy = HistoricoFilterProxyModel()
    proxy.setSourceModel(_build_source_model())
    return proxy


def test_filter_accepts_row_with_range_and_delegada() -> None:
    proxy = _build_proxy()
    proxy.set_filters(
        delegada_id=1,
        ver_todas=False,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=QDate(2026, 1, 1),
        date_to=QDate(2026, 1, 31),
    )

    expected = [
        RowExpectation(0, True),
        RowExpectation(1, True),
        RowExpectation(2, False),
        RowExpectation(3, False),
        RowExpectation(4, False),
        RowExpectation(5, False),
        RowExpectation(6, False),
        RowExpectation(7, False),
        RowExpectation(8, False),
    ]

    for check in expected:
        assert proxy.filterAcceptsRow(check.row, QModelIndex()) is check.accepted

    assert proxy.rowCount() == 2


def test_rowcount_changes_with_year_modes() -> None:
    proxy = _build_proxy()

    proxy.set_filters(
        delegada_id=None,
        ver_todas=True,
        year_mode="ALL_YEAR",
        year=2026,
        month=None,
        date_from=None,
        date_to=None,
    )
    assert proxy.rowCount() == 6

    proxy.set_filters(
        delegada_id=None,
        ver_todas=True,
        year_mode="YEAR_MONTH",
        year=2026,
        month=2,
        date_from=None,
        date_to=None,
    )
    assert proxy.rowCount() == 3


def test_toggle_ver_todas_and_delegada_id() -> None:
    proxy = _build_proxy()

    proxy.set_filters(
        delegada_id=2,
        ver_todas=True,
        year_mode=None,
        year=None,
        month=None,
        date_from=None,
        date_to=None,
    )
    assert proxy.rowCount() == 9

    proxy.set_filters(
        delegada_id=2,
        ver_todas=False,
        year_mode=None,
        year=None,
        month=None,
        date_from=None,
        date_to=None,
    )
    assert proxy.rowCount() == 3


def test_invalid_date_and_missing_fields_paths() -> None:
    proxy = _build_proxy()
    proxy.set_filters(
        delegada_id=None,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=QDate(2026, 2, 1),
        date_to=QDate(2026, 2, 29),
    )

    # fecha inválida => _coerce_to_date devuelve None; en RANGE no se excluye.
    assert proxy.filterAcceptsRow(6, QModelIndex()) is True

    # fecha faltante + campos textuales None no deben romper filtros de texto.
    proxy.set_search_text("pendiente")
    assert proxy.filterAcceptsRow(8, QModelIndex()) is True


def test_range_filter_normalizes_inverted_dates() -> None:
    proxy = _build_proxy()
    proxy.set_filters(
        delegada_id=None,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=QDate(2026, 3, 1),
        date_to=QDate(2026, 1, 1),
    )

    state = proxy.filter_state()
    assert state["from"] is not None
    assert state["to"] is not None
    assert state["from"] <= state["to"]
    assert proxy.rowCount() > 0
