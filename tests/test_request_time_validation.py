from app.domain.request_time import validate_request_inputs


def test_validate_request_inputs_partial_requires_range() -> None:
    errors = validate_request_inputs("12:00", "10:00", completo=False)
    assert "rango" in errors


def test_validate_request_inputs_completo_skips_time_fields() -> None:
    errors = validate_request_inputs(None, None, completo=True)
    assert errors == {}
