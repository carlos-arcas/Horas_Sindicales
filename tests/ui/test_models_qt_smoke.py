from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

QtCore = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.application.dto import PersonaDTO, ResultadoCrearSolicitudDTO, SolicitudDTO
from app.ui.controllers.solicitudes_controller import SolicitudesController
from app.ui.models_qt import PersonasTableModel, SolicitudesTableModel

Qt = QtCore.Qt


def _solicitud(solicitud_id: int | None = None) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2026-01-10",
        fecha_pedida="2026-01-10",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="obs",
        pdf_path=None,
        pdf_hash=None,
        notas="nota",
    )


def test_qt_models_smoke_data_access() -> None:
    personas_model = PersonasTableModel([PersonaDTO(id=1, nombre="Ana", genero="F", horas_mes=60, horas_ano=120)])
    assert personas_model.rowCount() == 1

    solicitudes_model = SolicitudesTableModel([_solicitud(5)], show_estado=True)
    assert solicitudes_model.rowCount() == 1
    idx = solicitudes_model.index(0, 0)
    assert solicitudes_model.data(idx, Qt.DisplayRole) == "2026-01-10"


def test_solicitudes_controller_smoke_on_add_and_confirmar_lote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.ui.controllers.solicitudes_controller.toast_success", lambda *a, **k: None)

    solicitud = _solicitud()
    use_cases = Mock()
    use_cases.buscar_duplicado.return_value = None
    use_cases.calcular_minutos_solicitud.return_value = 60
    use_cases.minutes_to_hours_float.return_value = 1.0
    use_cases.crear_resultado.return_value = ResultadoCrearSolicitudDTO(
        success=True,
        warnings=[],
        errores=[],
        entidad=replace(solicitud, id=10),
        saldos=None,
    )
    use_cases.confirmar_sin_pdf.return_value = ([replace(solicitud, id=10)], [], [])

    window = SimpleNamespace(
        _build_preview_solicitud=Mock(return_value=solicitud),
        _selected_pending_for_editing=Mock(return_value=None),
        _solicitud_use_cases=use_cases,
        _resolve_backend_conflict=Mock(return_value=True),
        _reload_pending_views=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _update_action_state=Mock(),
        _undo_last_added_pending=Mock(),
        _set_processing_state=Mock(),
        _show_critical_error=Mock(),
        _handle_duplicate_detected=Mock(return_value=False),
        notas_input=SimpleNamespace(toPlainText=Mock(return_value="ok"), setPlainText=Mock()),
        notifications=Mock(build_operation_context=Mock(return_value=None)),
        toast=Mock(),
        desde_input=SimpleNamespace(setFocus=Mock()),
    )

    controller = SolicitudesController(window)
    controller.on_add_pendiente()

    pendientes = [replace(solicitud, id=10)]
    result = controller.confirmar_lote(
        pendientes,
        correlation_id="cid-1",
        generar_pdf=False,
        pdf_path=str(tmp_path / "unused.pdf"),
    )

    assert use_cases.crear_resultado.called
    assert result[0] == [10]
