from __future__ import annotations

import pytest

from app.domain.time_utils import hm_to_minutes, minutes_to_hhmm, minutes_to_hm, parse_hhmm


@pytest.mark.parametrize(
    ("minutos", "esperado"),
    [
        (0, "00:00"),
        (1, "00:01"),
        (59, "00:59"),
        (60, "01:00"),
        (61, "01:01"),
        (135, "02:15"),
        (1440, "24:00"),
        (90.0, "01:30"),
        (90.4, "01:30"),
        (90.5, "01:30"),
        (90.6, "01:31"),
        ("90", "01:30"),
        ("1439", "23:59"),
    ],
)
def test_minutes_to_hhmm_cases(minutos: int | float | str, esperado: str) -> None:
    assert minutes_to_hhmm(minutos) == esperado


@pytest.mark.parametrize("valor", [None, "abc"])
def test_minutes_to_hhmm_rechaza_tipos_invalidos(valor: object) -> None:
    with pytest.raises(ValueError, match="minutos"):
        minutes_to_hhmm(valor)  # type: ignore[arg-type]


def test_minutes_to_hhmm_rechaza_valores_negativos() -> None:
    with pytest.raises(ValueError, match="no negativos"):
        minutes_to_hhmm(-1)


def test_minutes_to_hhmm_caso_limite_59() -> None:
    assert minutes_to_hhmm(59) == "00:59"


def test_minutes_to_hm_inverse_split() -> None:
    assert minutes_to_hm(135) == (2, 15)


def test_hm_to_minutes() -> None:
    assert hm_to_minutes(2, 15) == 135


def test_parse_hhmm_ok() -> None:
    assert parse_hhmm("02:15") == 135


@pytest.mark.parametrize("valor", ["25:00", "12:61", "foo", "12-30"])
def test_parse_hhmm_invalid(valor: str) -> None:
    with pytest.raises(ValueError):
        parse_hhmm(valor)
