from datetime import UTC, datetime

from app.ui.tiempo.parseo_iso_datetime import (
    duracion_ms_desde_iso,
    normalizar_zona_horaria,
    parsear_iso_datetime,
)


def test_parsear_iso_datetime_retorna_datetime() -> None:
    valor = parsear_iso_datetime("2026-01-01T10:00:00")
    assert isinstance(valor, datetime)


def test_normalizar_zona_horaria_convierte_aware() -> None:
    entrada = datetime.fromisoformat("2026-01-01T10:00:00+02:00")
    salida = normalizar_zona_horaria(entrada, UTC)
    assert salida.tzinfo is not None
    assert salida.isoformat() == "2026-01-01T08:00:00+00:00"


def test_duracion_ms_desde_iso_soporta_naive_y_aware() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:00:00", "2026-01-01T10:01:00+00:00", tz_objetivo=UTC
    )
    assert duracion >= 0


def test_duracion_ms_desde_iso_no_devuelve_negativo() -> None:
    duracion = duracion_ms_desde_iso(
        "2026-01-01T10:01:00+00:00", "2026-01-01T10:00:00+00:00", tz_objetivo=UTC
    )
    assert duracion == 0


def test_duracion_ms_desde_iso_iso_invalido_retorna_cero_y_loguea_warning(caplog) -> None:
    duracion = duracion_ms_desde_iso("invalido", "2026-01-01T10:00:00+00:00", tz_objetivo=UTC)
    assert duracion == 0
    assert "sync_report_datetime_invalido" in caplog.text
