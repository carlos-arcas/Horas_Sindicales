from __future__ import annotations

import pytest

QtCore = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.application.dto import SolicitudDTO
from app.ui.historico_view import HistoricoFilterProxyModel
from app.ui.models_qt import SolicitudesTableModel

QDate = QtCore.QDate


def _solicitud(solicitud_id: int, persona_id: int, fecha: str, generated: bool = False) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
        notas="",
        generated=generated,
    )


def test_historico_filter_proxy_set_filters_smoke() -> None:
    source = SolicitudesTableModel([
        _solicitud(1, 1, "2026-01-10", generated=False),
        _solicitud(2, 2, "2026-02-10", generated=True),
    ])
    proxy = HistoricoFilterProxyModel()
    proxy.setSourceModel(source)

    proxy.set_filters(
        delegada_id=1,
        ver_todas=False,
        year_mode="RANGE",
        year=2026,
        month=1,
        date_from=QDate(2026, 1, 1),
        date_to=QDate(2026, 1, 31),
    )

    assert isinstance(proxy.rowCount(), int)
    state = proxy.filter_state()
    assert state["delegada_id"] == 1
