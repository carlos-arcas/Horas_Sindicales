from __future__ import annotations

from app.application.sync_normalization import normalize_date, normalize_hhmm, solicitud_unique_key


def test_normalize_date_accepts_multiple_supported_formats() -> None:
    assert normalize_date("2025-02-01") == "2025-02-01"
    assert normalize_date("01/02/2025") == "2025-02-01"
    assert normalize_date("01-02-2025") == "2025-02-01"
    assert normalize_date("01/02/25") == "2025-02-01"
    assert normalize_date("01-02-25") == "2025-02-01"


def test_normalize_date_returns_none_for_empty_and_invalid_lengths() -> None:
    assert normalize_date("") is None
    assert normalize_date(None) is None
    assert normalize_date("abc") is None


def test_normalize_date_keeps_unknown_but_ten_char_value() -> None:
    assert normalize_date("2025.02.01") == "2025.02.01"


def test_normalize_hhmm_from_colon_and_minutes_input() -> None:
    assert normalize_hhmm("9:5") == "09:05"
    assert normalize_hhmm(" 10:30 ") == "10:30"
    assert normalize_hhmm("75") == "01:15"


def test_normalize_hhmm_rejects_invalid_values() -> None:
    assert normalize_hhmm("") is None
    assert normalize_hhmm(None) is None
    assert normalize_hhmm("ab:cd") is None
    assert normalize_hhmm("10") == "00:10"


def test_solicitud_unique_key_returns_none_without_delegada_or_date() -> None:
    assert solicitud_unique_key(None, "2025-02-01", False, "09:00", "10:00") is None
    assert solicitud_unique_key("uuid", "", False, "09:00", "10:00") is None


def test_solicitud_unique_key_normalizes_values_and_boolean_flag() -> None:
    assert solicitud_unique_key(" uuid ", "01/02/2025", 1, "9:5", "125") == (
        "uuid",
        "2025-02-01",
        True,
        "09:05",
        "02:05",
    )


def test_solicitud_unique_key_is_stable_for_equivalent_inputs() -> None:
    key_a = solicitud_unique_key("uuid", "2025-02-01", False, "60", "120")
    key_b = solicitud_unique_key("uuid", "01/02/2025", False, "01:00", "02:00")

    assert key_a == key_b
