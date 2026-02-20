from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.application.use_cases import sync_sheets_core


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("", ""),
        (date(2025, 1, 10), "2025-01-10"),
        (datetime(2025, 1, 10, 12, 0), "2025-01-10"),
        ("10/01/2025", "2025-01-10"),
        ("2025-01-10", "2025-01-10"),
        ("weird-format", "weird-format"),
    ],
)
def test_to_iso_date_supports_dates_and_fallbacks(raw, expected) -> None:
    assert sync_sheets_core.to_iso_date(raw) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("09:30", 570),
        (" 0:05 ", 5),
        ("abc:10", None),
        ("11", None),
        (None, None),
    ],
)
def test_parse_hhmm_to_minutes_handles_valid_and_invalid_values(value, expected) -> None:
    assert sync_sheets_core.parse_hhmm_to_minutes(value) == expected


def test_parse_iso_supports_zulu_and_naive_datetime() -> None:
    parsed_zulu = sync_sheets_core.parse_iso("2025-01-01T10:00:00Z")
    parsed_naive = sync_sheets_core.parse_iso("2025-01-01T10:00:00")

    assert parsed_zulu is not None and parsed_zulu.tzinfo is not None
    assert parsed_naive == datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("updated", "last_sync", "expected"),
    [
        ("2025-01-01T12:00:00+00:00", None, True),
        (None, "2025-01-01T11:00:00+00:00", False),
        ("invalid", "2025-01-01T11:00:00+00:00", False),
    ],
)
def test_is_after_last_sync_edge_cases(updated, last_sync, expected) -> None:
    assert sync_sheets_core.is_after_last_sync(updated, last_sync) is expected


def test_normalize_remote_row_uses_name_alias_and_lowercases_estado() -> None:
    row = {
        "delegada": "  Ana Delegada  ",
        "fecha": "2025-02-15",
        "desde_h": "7",
        "desde_m": "45",
        "hasta_h": "9",
        "hasta_m": "00",
        "estado": " PENDIENTE ",
    }

    normalized = sync_sheets_core.normalize_remote_solicitud_row(row, "Solicitudes")

    assert normalized["delegada_nombre"].strip() == "Ana Delegada"
    assert normalized["desde_h"] == 7
    assert normalized["desde_m"] == 45
    assert normalized["hasta_h"] == 9
    assert normalized["hasta_m"] == 0
    assert normalized["estado"] == "pendiente"
