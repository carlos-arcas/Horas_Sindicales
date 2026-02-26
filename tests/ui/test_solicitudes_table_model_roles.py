from __future__ import annotations

from PySide6.QtCore import Qt

from app.application.dto import SolicitudDTO
from app.ui.models_qt import SolicitudesTableModel
from app.ui.patterns import status_badge


def _solicitud(**kwargs) -> SolicitudDTO:
    base = {
        "id": 1,
        "persona_id": 11,
        "fecha_solicitud": "2026-01-09",
        "fecha_pedida": "2026-01-15",
        "desde": "09:00",
        "hasta": "11:00",
        "completo": False,
        "horas": 2.0,
        "observaciones": None,
        "pdf_path": None,
        "pdf_hash": None,
        "notas": "Nota interna",
        "generated": False,
    }
    base.update(kwargs)
    return SolicitudDTO(**base)


def test_data_display_dynamic_columns_respect_estado_and_delegada():
    model = SolicitudesTableModel([_solicitud(generated=True)], show_estado=True)
    model.set_show_delegada(True)
    model.set_persona_nombres({11: "Ana"})

    estado_index = model.index(0, 6)
    delegada_index = model.index(0, 7)

    assert model.data(estado_index, Qt.DisplayRole) == status_badge("CONFIRMED")
    assert model.data(delegada_index, Qt.DisplayRole) == "Ana"


def test_data_tooltip_prefers_notas_column_and_marks_conflicts_in_fecha():
    model = SolicitudesTableModel([_solicitud()])
    model.set_conflict_rows({0})

    notas_index = model.index(0, 5)
    fecha_index = model.index(0, 0)

    assert model.data(notas_index, Qt.ToolTipRole) == "Nota interna"
    assert model.data(fecha_index, Qt.ToolTipRole) == "⚠ Horario solapado con otra petición pendiente del mismo día."


def test_data_conflict_styles_apply_only_on_fecha_column():
    model = SolicitudesTableModel([_solicitud()])
    model.set_conflict_rows({0})

    fecha_index = model.index(0, 0)
    desde_index = model.index(0, 1)

    foreground = model.data(fecha_index, Qt.ForegroundRole)
    font = model.data(fecha_index, Qt.FontRole)

    assert foreground.name() == "#c62828"
    assert font.underline()
    assert model.data(desde_index, Qt.ForegroundRole) is None
    assert model.data(desde_index, Qt.FontRole) is None
