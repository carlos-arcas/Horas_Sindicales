from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.application.use_cases.alert_engine import AlertEngine
from app.domain.sync_models import HealthCheckItem, HealthReport, SyncReport


def _health(*checks: HealthCheckItem) -> HealthReport:
    return HealthReport(generated_at="2026-01-10T12:00:00", checks=checks)


def _report(**kwargs: object) -> SyncReport:
    base = replace(SyncReport.empty(), status="OK", final_status="OK", finished_at="2026-01-10T10:00:00")
    return replace(base, **kwargs)


def test_alert_engine_stale_sin_historial() -> None:
    engine = AlertEngine(now_provider=lambda: datetime(2026, 1, 10, 12, 0, 0))

    alerts = engine.evaluate(history=[], health_report=_health(), pending_count=0)

    assert any(a.key == "stale_sync" and "Aún no hay sincronizaciones" in a.message for a in alerts)


def test_alert_engine_high_failure_rate_y_config_incompleta() -> None:
    engine = AlertEngine(now_provider=lambda: datetime(2026, 1, 10, 12, 0, 0))
    history = [
        _report(status="ERROR"),
        _report(status="CONFIG_INCOMPLETE"),
        _report(status="OK"),
    ]
    health = _health(HealthCheckItem(key="cfg", status="ERROR", message="x", category="Configuración", action_id="open"))

    alerts = engine.evaluate(history=history, health_report=health, pending_count=2)
    keys = {a.key for a in alerts}

    assert {"high_failure_rate", "config_incomplete", "pending_local_changes"}.issubset(keys)


def test_alert_engine_respeta_silencio_y_timestamp_invalido() -> None:
    now = datetime(2026, 1, 10, 12, 0, 0)
    engine = AlertEngine(stale_days=7, now_provider=lambda: now)
    old_history = [_report(finished_at="2026-01-01T00:00:00")]

    silenced = {"stale_sync": "2026-01-20T00:00:00"}
    alerts_silenced = engine.evaluate(history=old_history, health_report=_health(), pending_count=0, silenced_until=silenced)
    assert all(a.key != "stale_sync" for a in alerts_silenced)

    invalid_ts_history = [_report(finished_at="not-an-iso")]
    alerts_invalid_ts = engine.evaluate(history=invalid_ts_history, health_report=_health(), pending_count=0)
    assert all(a.key != "stale_sync" for a in alerts_invalid_ts)
