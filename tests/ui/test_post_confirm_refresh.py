from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.application.dto import SolicitudDTO
from app.ui.controllers.solicitudes_controller import SolicitudesController


def _solicitud(sid: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def test_post_confirm_controller_aplica_confirmacion_y_deja_un_pendiente() -> None:
    use_cases = Mock()
    use_cases.listar_historico.return_value = []
    window = SimpleNamespace(
        _solicitud_use_cases=use_cases,
        _pending_all_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        _pending_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        _hidden_pendientes=[_solicitud(2)],
        _pending_otras_delegadas=[_solicitud(2)],
        _orphan_pendientes=[_solicitud(3)],
    )
    controller = SolicitudesController(window)

    controller.aplicar_confirmacion(confirmadas_ids=[1, 2], pendientes_restantes=[_solicitud(3)])

    assert [s.id for s in window._pending_solicitudes] == [3]
    assert [s.id for s in window._pending_all_solicitudes] == [3]
    assert window._hidden_pendientes == []
    assert window._pending_otras_delegadas == []
    assert [s.id for s in window._orphan_pendientes] == [3]


def test_post_confirm_controller_aplica_confirmacion_sin_pendientes_restantes() -> None:
    use_cases = Mock()
    use_cases.listar_historico.return_value = []
    window = SimpleNamespace(
        _solicitud_use_cases=use_cases,
        _pending_all_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        _pending_solicitudes=[_solicitud(2), _solicitud(3)],
        _hidden_pendientes=[_solicitud(2)],
        _pending_otras_delegadas=[_solicitud(2), _solicitud(9)],
        _orphan_pendientes=[_solicitud(2), _solicitud(7)],
    )
    controller = SolicitudesController(window)

    controller.aplicar_confirmacion(confirmadas_ids=[2], pendientes_restantes=None)

    assert [s.id for s in window._pending_all_solicitudes] == [1, 3]
    assert [s.id for s in window._pending_solicitudes] == [3]
    assert window._hidden_pendientes == []
    assert [s.id for s in window._pending_otras_delegadas] == [9]
    assert [s.id for s in window._orphan_pendientes] == [7]


def test_post_confirm_controller_aplica_confirmacion_y_no_deja_zombies_si_no_hay_pendientes() -> None:
    use_cases = Mock()
    use_cases.listar_historico.return_value = []
    window = SimpleNamespace(
        _solicitud_use_cases=use_cases,
        _pending_all_solicitudes=[_solicitud(1), _solicitud(2)],
        _pending_solicitudes=[_solicitud(1), _solicitud(2)],
        _hidden_pendientes=[_solicitud(2)],
        _pending_otras_delegadas=[_solicitud(2)],
        _orphan_pendientes=[_solicitud(2)],
    )
    controller = SolicitudesController(window)

    controller.aplicar_confirmacion(confirmadas_ids=[1, 2], pendientes_restantes=[])

    assert window._pending_all_solicitudes == []
    assert window._pending_solicitudes == []
    assert window._hidden_pendientes == []
    assert window._pending_otras_delegadas == []
    assert window._orphan_pendientes == []


def test_post_confirm_controller_recarga_historico_una_vez() -> None:
    historico = [_solicitud(99)]
    use_cases = Mock()
    use_cases.listar_historico.return_value = historico
    window = SimpleNamespace(_solicitud_use_cases=use_cases)
    controller = SolicitudesController(window)

    result = controller.refresh_historico()

    assert result == historico
    use_cases.listar_historico.assert_called_once_with()
