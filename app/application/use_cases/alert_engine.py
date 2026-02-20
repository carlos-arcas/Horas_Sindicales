from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from app.domain.sync_models import Alert, HealthReport, SyncReport


class AlertEngine:
    def __init__(self, stale_days: int = 7, now_provider=None) -> None:
        self._stale_days = stale_days
        self._now_provider = now_provider or datetime.now

    def evaluate(
        self,
        *,
        history: list[SyncReport],
        health_report: HealthReport,
        pending_count: int,
        silenced_until: dict[str, str] | None = None,
    ) -> list[Alert]:
        now = self._now_provider()
        silenced_until = silenced_until or {}
        alerts: list[Alert] = []

        stale_alert = self._build_stale_sync_alert(history, now)
        if stale_alert is not None:
            alerts.append(stale_alert)

        if self._is_high_failure_rate(history):
            alerts.append(
                Alert(
                    key="high_failure_rate",
                    severity="WARN",
                    message="La tasa de fallos en las últimas sincronizaciones es alta (>=30%).",
                    action_id="open_sync_panel",
                )
            )

        if self._has_repeated_conflicts(history):
            alerts.append(
                Alert(
                    key="repeated_conflicts",
                    severity="WARN",
                    message="Hay conflictos repetidos del mismo registro (3 veces).",
                    action_id="open_conflicts",
                )
            )

        if any(check.status == "ERROR" and check.category == "Configuración" for check in health_report.checks):
            alerts.append(
                Alert(
                    key="config_incomplete",
                    severity="ERROR",
                    message="La configuración de sincronización está incompleta y bloquea la sync.",
                    action_id="open_sync_settings",
                )
            )

        if pending_count > 0:
            alerts.append(
                Alert(
                    key="pending_local_changes",
                    severity="WARN",
                    message=f"Hay {pending_count} cambios locales pendientes de sincronizar.",
                    action_id="open_sync_panel",
                )
            )

        return [alert for alert in alerts if not self._is_silenced(alert, silenced_until, now)]

    def _build_stale_sync_alert(self, history: list[SyncReport], now: datetime) -> Alert | None:
        if not history:
            return Alert(
                key="stale_sync",
                severity="WARN",
                message="Aún no hay sincronizaciones registradas.",
                action_id="open_sync_panel",
            )
        latest = history[0]
        last_time = self._parse_iso(latest.finished_at)
        if last_time is None:
            return None
        if now - last_time >= timedelta(days=self._stale_days):
            return Alert(
                key="stale_sync",
                severity="WARN",
                message=f"No sincronizas desde hace {self._stale_days} días o más.",
                action_id="open_sync_panel",
            )
        return None

    @staticmethod
    def _is_high_failure_rate(history: list[SyncReport]) -> bool:
        sample = history[:5]
        if not sample:
            return False
        failures = sum(1 for report in sample if report.status in {"ERROR", "CONFIG_INCOMPLETE"})
        return (failures / len(sample)) >= 0.3

    @staticmethod
    def _has_repeated_conflicts(history: list[SyncReport]) -> bool:
        labels: list[str] = []
        for report in history[:10]:
            labels.extend(report.conflicts)
        if not labels:
            return False
        counter = Counter(labels)
        return any(total >= 3 for total in counter.values())

    @staticmethod
    def _is_silenced(alert: Alert, silenced_until: dict[str, str], now: datetime) -> bool:
        until = silenced_until.get(alert.key)
        if not until:
            return False
        parsed = AlertEngine._parse_iso(until)
        return parsed is not None and parsed > now

    @staticmethod
    def _parse_iso(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
