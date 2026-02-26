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
        _orphan_pendientes=[_solicitud(3)],
    )
    controller = SolicitudesController(window)

    controller.aplicar_confirmacion(confirmadas_ids=[1, 2], pendientes_restantes=[_solicitud(3)])

    assert [s.id for s in window._pending_solicitudes] == [3]


def test_post_confirm_controller_recarga_historico_una_vez() -> None:
    historico = [_solicitud(99)]
    use_cases = Mock()
    use_cases.listar_historico.return_value = historico
    window = SimpleNamespace(_solicitud_use_cases=use_cases)
    controller = SolicitudesController(window)

    result = controller.refresh_historico()

    assert result == historico
    use_cases.listar_historico.assert_called_once_with()
