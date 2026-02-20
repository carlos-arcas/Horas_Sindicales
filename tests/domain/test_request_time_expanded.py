from __future__ import annotations

import pytest

from app.domain.request_time import compute_request_minutes, minutes_to_hours_float, validate_request_inputs
from app.domain.services import BusinessRuleError


@pytest.mark.parametrize(
    ("desde", "hasta", "completo", "field"),
    [
        (None, "10:00", False, "desde"),
        ("09:00", None, False, "hasta"),
        ("09:00", "09:00", False, "rango"),
    ],
)
def test_validate_request_inputs_reports_expected_error_fields(desde, hasta, completo, field) -> None:
    errors = validate_request_inputs(desde, hasta, completo)
    assert field in errors


@pytest.mark.parametrize("cuadrante_base", [0, None, -30])
def test_compute_request_minutes_rejects_non_positive_full_day(cuadrante_base) -> None:
    with pytest.raises(BusinessRuleError):
        compute_request_minutes(None, None, completo=True, cuadrante_base=cuadrante_base)


def test_minutes_to_hours_float_rejects_negative_values() -> None:
    with pytest.raises(BusinessRuleError):
        minutes_to_hours_float(-1)


def test_validate_request_inputs_propagates_invalid_time_format() -> None:
    with pytest.raises(ValueError):
        validate_request_inputs("invalid", "10:00", completo=False)
