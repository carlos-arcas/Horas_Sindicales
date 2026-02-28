from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

from app.application.dto import PersonaDTO, SolicitudDTO

pytestmark = pytest.mark.headless_safe


class _FakeQt:
    DisplayRole = 0
    EditRole = 1
    ToolTipRole = 2
    ForegroundRole = 3
    FontRole = 4
    Horizontal = 10
    Vertical = 11
    UserRole = 1000


class _FakeModelIndex:
    def __init__(self, row: int = -1, column: int = -1, valid: bool = False) -> None:
        self._row = row
        self._column = column
        self._valid = valid

    def row(self) -> int:
        return self._row

    def column(self) -> int:
        return self._column

    def isValid(self) -> bool:
        return self._valid


class _FakeQAbstractTableModel:
    def beginResetModel(self) -> None:  # pragma: no cover - no-op stub
        return None

    def endResetModel(self) -> None:  # pragma: no cover - no-op stub
        return None

    def beginInsertRows(self, *_args) -> None:  # pragma: no cover - no-op stub
        return None

    def endInsertRows(self) -> None:  # pragma: no cover - no-op stub
        return None

    def index(self, row: int, column: int) -> _FakeModelIndex:
        valid = row >= 0 and column >= 0
        return _FakeModelIndex(row, column, valid=valid)

    def flags(self, _index: _FakeModelIndex) -> int:
        return 0


class _FakeQColor:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeQFont:
    def __init__(self) -> None:
        self.underline = False

    def setUnderline(self, value: bool) -> None:
        self.underline = value


def _install_qt_stubs() -> None:
    pyside = ModuleType("PySide6")

    qtcore = ModuleType("PySide6.QtCore")
    qtcore.QAbstractTableModel = _FakeQAbstractTableModel
    qtcore.QModelIndex = _FakeModelIndex
    qtcore.Qt = _FakeQt

    qtgui = ModuleType("PySide6.QtGui")
    qtgui.QColor = _FakeQColor
    qtgui.QFont = _FakeQFont

    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui


def _load_models_qt():
    _install_qt_stubs()
    sys.modules.pop("app.ui.models_qt", None)
    return importlib.import_module("app.ui.models_qt")


def _persona(pid: int, nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=pid,
        nombre=nombre,
        genero="F",
        horas_mes=90,
        horas_ano=120,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def _solicitud(
    sid: int,
    *,
    fecha_pedida: str = "2026-01-10",
    horas: float = 1.5,
    generated: bool = False,
    notas: str | None = "nota",
) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=1,
        fecha_solicitud="2026-01-10",
        fecha_pedida=fecha_pedida,
        desde="09:00",
        hasta="10:30",
        completo=False,
        horas=horas,
        observaciones="obs",
        pdf_path=None,
        pdf_hash=None,
        notas=notas,
        generated=generated,
    )


def test_personas_table_model_contract() -> None:
    models_qt = _load_models_qt()
    Qt = models_qt.Qt

    model = models_qt.PersonasTableModel([_persona(1, "Ana")])

    assert model.rowCount() == 1
    assert model.columnCount() == 4
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Nombre"
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) == "1"
    assert model.headerData(0, Qt.Horizontal, Qt.EditRole) is None
    assert model.persona_at(0).nombre == "Ana"
    assert model.persona_at(99) is None

    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Ana"
    assert model.data(model.index(0, 2), Qt.DisplayRole) == "01:30"
    assert model.data(model.index(0, 3), Qt.DisplayRole) == "02:00"
    assert model.data(models_qt.QModelIndex(), Qt.DisplayRole) is None
    assert model.data(model.index(0, 1), Qt.EditRole) is None

    model.set_personas([_persona(2, "Bea")])
    assert model.rowCount() == 1
    assert model.persona_at(0).nombre == "Bea"
    assert model.flags(model.index(0, 0)) == 0


def test_solicitudes_table_model_display_and_dynamic_columns() -> None:
    models_qt = _load_models_qt()
    Qt = models_qt.Qt

    sol = _solicitud(10, generated=True)
    model = models_qt.SolicitudesTableModel([sol], show_estado=True)

    assert model.rowCount() == 1
    assert model.columnCount() == 7
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "2026-01-10"
    assert model.data(model.index(0, 1), Qt.DisplayRole) == "09:00"
    assert model.data(model.index(0, 3), Qt.DisplayRole) == "No"
    assert model.data(model.index(0, 4), Qt.DisplayRole) == "01:30"
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "nota"
    assert model.data(model.index(0, 6), Qt.DisplayRole) == "✅ Confirmada"

    role_value = model.data(model.index(0, 0), models_qt.SOLICITUD_FECHA_ROLE)
    assert str(role_value) == "2026-01-10"

    model.set_show_delegada(True)
    model.set_persona_nombres({1: "Ana"})
    assert model.columnCount() == 8
    assert model.data(model.index(0, 7), Qt.DisplayRole) == "Ana"

    model.append_solicitud(_solicitud(11, fecha_pedida="invalida", horas=-2.0, notas=None))
    assert model.rowCount() == 2
    assert model.data(model.index(1, 4), Qt.DisplayRole) == "-02:00"
    assert model.fecha_pedida_date_at(1) is None
    assert model.solicitud_at(1).id == 11
    assert model.solicitud_at(42) is None


def test_solicitudes_table_model_roles_and_mutations() -> None:
    models_qt = _load_models_qt()
    Qt = models_qt.Qt

    model = models_qt.SolicitudesTableModel([_solicitud(1, notas=None)], show_estado=False)
    model.set_conflict_rows({0})

    index_fecha = model.index(0, 0)
    index_notas = model.index(0, 5)

    assert model.data(index_notas, Qt.ToolTipRole) == ""
    assert "solapado" in model.data(index_fecha, Qt.ToolTipRole)
    color = model.data(index_fecha, Qt.ForegroundRole)
    assert color.value == "#c62828"
    font = model.data(index_fecha, Qt.FontRole)
    assert font.underline is True
    assert model.data(index_fecha, 99999) is None

    assert model.headerData(99, Qt.Horizontal, Qt.DisplayRole) is None
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) == "1"

    pending = _solicitud(2, generated=False)
    model.set_solicitudes([pending])
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "nota"

    assert model.persona_name_for_id(999) == ""
    model.set_persona_nombres({1: "Delegada"})
    model.set_show_delegada(True)
    assert model.persona_name_for_id(1) == "Delegada"

    assert len(model.solicitudes()) == 1
    model.clear()
    assert model.rowCount() == 0
    assert model.fecha_pedida_date_at(0) is None
