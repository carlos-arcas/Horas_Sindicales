from __future__ import annotations

from app.domain.time_utils import minutes_to_hhmm


def test_minutes_to_hhmm_accepts_int_minutes() -> None:
    assert minutes_to_hhmm(90) == "01:30"


def test_minutes_to_hhmm_accepts_float_minutes() -> None:
    assert minutes_to_hhmm(90.0) == "01:30"
