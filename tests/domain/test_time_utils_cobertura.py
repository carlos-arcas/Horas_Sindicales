from __future__ import annotations

import math

import pytest

from app.domain.time_utils import hm_to_minutes, horas_decimales_a_minutos, minutes_to_hhmm, parse_hhmm


def test_hm_to_minutes_rechaza_valores_negativos() -> None:
    with pytest.raises(ValueError, match="no negativos"):
        hm_to_minutes(-1, 10)


def test_horas_decimales_a_minutos_cubre_casos_invalidos_y_nan() -> None:
    assert horas_decimales_a_minutos(None) == 0
    assert horas_decimales_a_minutos("1.5") == 90
    assert horas_decimales_a_minutos(math.nan) == 0

    with pytest.raises(ValueError, match="número válido"):
        horas_decimales_a_minutos("abc")
    with pytest.raises(ValueError, match="número válido"):
        horas_decimales_a_minutos(True)
    with pytest.raises(ValueError, match="no negativas"):
        horas_decimales_a_minutos(-0.1)


def test_parse_hhmm_valida_formato_y_rango() -> None:
    assert parse_hhmm("08:15") == 495

    with pytest.raises(ValueError, match="Formato inválido"):
        parse_hhmm("0815")
    with pytest.raises(ValueError, match="Hora fuera de rango"):
        parse_hhmm("24:00")


def test_minutes_to_hhmm_normaliza_string_nan_y_negativos() -> None:
    assert minutes_to_hhmm(" 90.6 ") == "01:31"
    assert minutes_to_hhmm(float("nan")) == "00:00"

    with pytest.raises(ValueError, match="número válido"):
        minutes_to_hhmm(False)
    with pytest.raises(ValueError, match="número válido"):
        minutes_to_hhmm("no-num")
    with pytest.raises(ValueError, match="no negativos"):
        minutes_to_hhmm(-1)
