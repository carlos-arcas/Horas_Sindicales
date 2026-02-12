from __future__ import annotations

import pytest

from app.domain.request_time import compute_request_minutes
from app.domain.services import BusinessRuleError


def test_calculo_desde_hasta_hhmm() -> None:
    assert compute_request_minutes("09:15", "11:45", completo=False) == 150


def test_calculo_jornada_completa_usa_cuadrante_base() -> None:
    assert compute_request_minutes(None, None, completo=True, cuadrante_base=420) == 420


def test_falla_parcial_sin_intervalo() -> None:
    with pytest.raises(BusinessRuleError):
        compute_request_minutes(None, "11:00", completo=False)


def test_falla_intervalo_invertido() -> None:
    with pytest.raises(BusinessRuleError):
        compute_request_minutes("12:00", "10:00", completo=False)
