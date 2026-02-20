from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import Mock

from app.application.dtos.contexto_operacion import ContextoOperacion
from app.application.use_cases.solicitudes.use_case import SolicitudUseCases


def test_eliminar_solicitud_loguea_correlation_id_del_contexto(caplog) -> None:
    repo = Mock()
    repo.get_by_id.return_value = SimpleNamespace(fecha_pedida="2024-01-01", persona_id=7)

    use_case = SolicitudUseCases(repo=repo, persona_repo=Mock())
    fake_saldos = object()
    use_case.calcular_saldos = Mock(return_value=fake_saldos)  # type: ignore[method-assign]

    contexto = ContextoOperacion(correlation_id="cid-fijo-123", result_id="OP-0001")

    with caplog.at_level(logging.INFO):
        result = use_case.eliminar_solicitud(42, contexto=contexto)

    assert result is fake_saldos
    assert any(getattr(record, "correlation_id", None) == "cid-fijo-123" for record in caplog.records)
    assert repo.delete.called
