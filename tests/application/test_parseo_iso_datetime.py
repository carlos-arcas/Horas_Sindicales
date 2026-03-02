import logging
from datetime import UTC, datetime

import pytest

from app.ui.tiempo.parseo_iso_datetime import (
    duracion_ms_desde_iso,
    normalizar_zona_horaria,
    parsear_iso_datetime,
)


def test_parsear_iso_datetime_retorna_datetime() -> None:
    valor = parsear_iso_datetime("2026-01-01T10:00:00")
    assert isinstance(valor, datetime)


def test_parsear_iso_datetime_loguea_iso_invalido(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            parsear_iso_datetime("invalido")

    assert caplog.records[-1].evento == "iso_datetime_invalido"
    assert caplog.records[-1].iso == "invalido"


def test_normalizar_zona_horaria_convierte_aware() -> None:
    entrada = datetime.fromisoformat("2026-01-01T10:00:00+02:00")
    salida = normalizar_zona_horaria(entrada, UTC)
    assert salida.tzinfo is not None
    assert salida.isoformat() == "2026-01-01T08:00:00+00:00"


def test_normalizar_zona_horaria_naive_loguea_normalizacion(caplog) -> None:
    with caplog.at_level(logging.INFO):
        salida = normalizar_zona_horaria(
            datetime.fromisoformat("2026-01-01T10:00:00"), UTC
        )

    assert salida.tzinfo is not None
    assert caplog.records[-1].evento == "normalizacion_tz_naive_local"


def test_duracion_ms_desde_iso_soporta_naive_y_aware() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:00:00", "2026-01-01T10:01:00+00:00", tz_objetivo=UTC
    )
    assert duracion >= 0


def test_duracion_ms_desde_iso_soporta_now_naive_y_generated_aware() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:00:00+00:00", "2026-01-01T10:01:00", tz_objetivo=UTC
    )
    assert duracion >= 0


def test_duracion_ms_desde_iso_soporta_ambos_naive() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:00:00", "2026-01-01T10:01:00", tz_objetivo=UTC
    )
    assert duracion >= 0


def test_duracion_ms_desde_iso_iso_invalido_devuelve_cero() -> None:
    duracion = duracion_ms_desde_iso("no-es-fecha", "2026-01-01T10:01:00", tz_objetivo=UTC)
    assert duracion == 0


def test_duracion_ms_desde_iso_reproduce_bug_typeerror_naive_aware() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:00:00+00:00", "2026-01-01T10:01:00", tz_objetivo=UTC
    )
    assert isinstance(duracion, int)


def test_duracion_ms_desde_iso_no_devuelve_negativo() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:01:00+00:00", "2026-01-01T10:00:00+00:00", tz_objetivo=UTC
    )
    assert duracion == 0
