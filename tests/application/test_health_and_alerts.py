from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.health_check import HealthCheckUseCase
from app.domain.sync_models import HealthReport, SyncReport, SyncSummary
from app.ui.sync_reporting import build_sync_report, load_sync_report, persist_report


class _SchemaProbe:
    def __init__(self, payload):
        self.payload = payload

    def check(self):
        return self.payload


class _ConnectivityProbe:
    def check(self, *, timeout_seconds: float = 3.0):
        return True, True, 120.0, "Latencia aproximada API: 120 ms."


class _DbProbe:
    def check(self):
        return {
            "local_db": (True, "Base de datos local accesible.", "open_db_help"),
            "migrations": (True, "Migraciones al día.", "open_db_help"),
            "ghost_pending": (True, "No se detectan pendientes fantasma.", "open_sync_panel"),
        }


def _dummy_health() -> HealthReport:
    return HealthReport(generated_at=datetime.now().isoformat(), checks=tuple())


def test_health_check_config_incompleta_devuelve_error_y_accion() -> None:
    use_case = HealthCheckUseCase(
        _SchemaProbe({"credentials": (False, "Falta configurar credenciales", "open_sync_settings")}),
        _ConnectivityProbe(),
        _DbProbe(),
    )

    report = use_case.run()

    credentials = next(check for check in report.checks if check.key == "credentials")
    assert credentials.status == "ERROR"
    assert credentials.action_id == "open_sync_settings"


def test_alert_engine_alerta_si_mas_de_7_dias_sin_sync() -> None:
    engine = AlertEngine(stale_days=7, now_provider=lambda: datetime(2026, 1, 10, 10, 0, 0))
    history = [replace(SyncReport.empty(), finished_at="2026-01-01T09:00:00", status="OK", final_status="OK")]

    alerts = engine.evaluate(history=history, health_report=_dummy_health(), pending_count=0)

    assert any(alert.key == "stale_sync" for alert in alerts)


def test_alert_engine_alerta_conflictos_repetidos() -> None:
    engine = AlertEngine(now_provider=lambda: datetime(2026, 1, 10, 10, 0, 0))
    base = replace(SyncReport.empty(), status="WARN", final_status="WARN")
    history = [
        replace(base, conflicts=["uuid-1"]),
        replace(base, conflicts=["uuid-1"]),
        replace(base, conflicts=["uuid-1"]),
    ]

    alerts = engine.evaluate(history=history, health_report=_dummy_health(), pending_count=0)

    assert any(alert.key == "repeated_conflicts" for alert in alerts)


def test_metricas_syncreport_se_guardan_en_historial(tmp_path) -> None:
    report = build_sync_report(
        SyncSummary(inserted_local=2, updated_remote=1),
        status="OK",
        source="src",
        scope="all",
        actor="delegada",
        rows_total_local=12,
        rows_scanned_remote=8,
        api_calls_count=5,
    )

    persist_report(report, tmp_path)
    saved = load_sync_report(sorted((tmp_path / "logs" / "sync_history").glob("*.json"))[0])

    assert saved.duration_ms >= 0
    assert saved.rows_total_local == 12
    assert saved.rows_scanned_remote == 8
    assert saved.api_calls_count == 5
