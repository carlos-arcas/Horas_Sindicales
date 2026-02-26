from __future__ import annotations

import pytest

from app.domain.time_range import TimeRangeValidationError, normalize_range, overlaps


def test_overlaps_no_solapa_si_fin_igual_inicio() -> None:
    assert overlaps(17 * 60, 18 * 60, 18 * 60, 19 * 60) is False


def test_overlaps_solape_parcial() -> None:
    assert overlaps(10 * 60, 12 * 60, 11 * 60, 13 * 60) is True


def test_overlaps_solape_total() -> None:
    assert overlaps(10 * 60, 15 * 60, 11 * 60, 12 * 60) is True


def test_normalize_range_completo_vs_parcial() -> None:
    completo = normalize_range(completo=True)
    parcial = normalize_range(completo=False, desde="09:00", hasta="10:00")

    assert overlaps(*completo, *parcial) is True


def test_0000_0000_no_es_completo_si_flag_es_false() -> None:
    with pytest.raises(TimeRangeValidationError, match="duración mayor de 0"):
        normalize_range(completo=False, desde="00:00", hasta="00:00")
