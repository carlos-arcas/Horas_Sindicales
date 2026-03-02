from datetime import datetime

from app.ui import sync_reporting
from app.ui.sync_reporting import duracion_ms_desde_iso


def _set_now_iso(monkeypatch, now_iso: str) -> None:
    class FakeDateTime:
        @staticmethod
        def fromisoformat(value: str) -> datetime:
            return datetime.fromisoformat(value)

        @staticmethod
        def now() -> datetime:
            return datetime.fromisoformat(now_iso)

    monkeypatch.setattr(sync_reporting, "datetime", FakeDateTime)


def test_duracion_ms_desde_iso_now_aware_y_generated_naive(monkeypatch) -> None:
    _set_now_iso(monkeypatch, "2026-01-01T10:01:00+00:00")
    duracion_ms = duracion_ms_desde_iso("2026-01-01T10:00:00", sync_reporting.datetime.now().isoformat())
    assert duracion_ms == 60000


def test_duracion_ms_desde_iso_now_naive_y_generated_aware(monkeypatch) -> None:
    _set_now_iso(monkeypatch, "2026-01-01T10:01:00")
    duracion_ms = duracion_ms_desde_iso("2026-01-01T10:00:00+00:00", sync_reporting.datetime.now().isoformat())
    assert duracion_ms == 60000


def test_duracion_ms_desde_iso_ambos_naive(monkeypatch) -> None:
    _set_now_iso(monkeypatch, "2026-01-01T10:01:00")
    duracion_ms = duracion_ms_desde_iso("2026-01-01T10:00:00", sync_reporting.datetime.now().isoformat())
    assert duracion_ms == 60000


def test_duracion_ms_desde_iso_iso_invalido_devuelve_cero() -> None:
    assert duracion_ms_desde_iso("esto-no-es-iso", "2026-01-01T10:01:00+00:00") == 0


def test_reproduce_bug_naive_vs_aware_no_lanza_typeerror(monkeypatch) -> None:
    _set_now_iso(monkeypatch, "2026-01-01T10:01:00")
    duracion_ms = duracion_ms_desde_iso("2026-01-01T10:00:00+00:00", sync_reporting.datetime.now().isoformat())
    assert duracion_ms >= 0
