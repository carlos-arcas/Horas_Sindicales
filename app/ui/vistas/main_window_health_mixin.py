from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem

from app.domain.sync_models import Alert, HealthReport
from app.domain.time_utils import minutes_to_hhmm
from app.ui.sync_reporting import list_sync_history, load_sync_report

logger = logging.getLogger(__name__)


class MainWindowHealthMixin:
    def _refresh_health_and_alerts(self) -> None:
        if self._health_check_use_case is None:
            self.health_summary_label.setText("Estado general: monitorización no configurada")
            self.alert_banner_label.setText("Alertas: monitorización no disponible.")
            return
        report = self._health_check_use_case.run()
        self._render_health_report(report)
        history = [load_sync_report(path) for path in list_sync_history(Path.cwd())[:5]]
        pending_count = len(list(self._solicitud_use_cases.listar_pendientes_all()))
        alerts = self._alert_engine.evaluate(
            history=history,
            health_report=report,
            pending_count=pending_count,
            silenced_until=self._alert_snooze,
        )
        self._render_alerts(alerts)

    def _render_health_report(self, report: HealthReport) -> None:
        self.health_checks_tree.clear()
        worst = "OK"
        for check in report.checks:
            if check.status == "ERROR":
                worst = "ERROR"
            elif check.status == "WARN" and worst != "ERROR":
                worst = "WARN"
            item = QTreeWidgetItem([check.status, check.category, check.message, "Solucionar"])
            item.setData(0, Qt.UserRole, check.action_id)
            self.health_checks_tree.addTopLevelItem(item)
        self.health_summary_label.setText(f"Estado general: {worst} · actualizado {self._format_timestamp(report.generated_at)}")

    def _render_alerts(self, alerts: list[Alert]) -> None:
        if not alerts:
            self.alert_banner_label.setText("Alertas: sin alertas activas.")
            return
        top = alerts[0]
        self.alert_banner_label.setText(f"Alerta {top.severity}: {top.message} · Acción: {top.action_id}")

    def _on_health_check_action(self, item: QTreeWidgetItem) -> None:
        action_id = item.data(0, Qt.UserRole)
        self._execute_action(action_id)

    def _execute_action(self, action_id: str) -> None:
        if action_id == "open_sync_settings":
            self._on_open_opciones()
            return
        if action_id == "open_sync_panel":
            self.main_tabs.setCurrentIndex(3)
            return
        if action_id == "open_conflicts":
            self._on_review_conflicts()
            return
        if action_id == "open_network_help":
            QMessageBox.information(self, "Conectividad", "Revisa tu conexión de red o VPN y vuelve a intentar.")
            return
        if action_id == "open_db_help":
            QMessageBox.information(self, "Base de datos", "Reinicia la aplicación y ejecuta migraciones si procede.")

    def _on_snooze_alerts_today(self) -> None:
        until = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        for key in ["stale_sync", "high_failure_rate", "repeated_conflicts", "config_incomplete", "pending_local_changes"]:
            self._alert_snooze[key] = until
        self._refresh_health_and_alerts()

    def _refresh_sync_trend_label(self) -> None:
        history = [load_sync_report(path) for path in list_sync_history(Path.cwd())[:5]]
        if not history:
            self.sync_trend_label.setText("Tendencia (5): --")
            return
        chunks = [f"{report.status}:{report.duration_ms}ms" for report in history]
        self.sync_trend_label.setText("Tendencia (5): " + " · ".join(chunks))

    def _refresh_last_sync_label(self) -> None:
        last_sync = self._sync_service.get_last_sync_at()
        if not last_sync:
            self.last_sync_label.setText("Última sync: Nunca")
            return
        formatted = self._format_timestamp(last_sync)
        self.last_sync_label.setText(f"Última sync: {formatted} · Delegada: {self._sync_actor_text()} · Alcance: {self._sync_scope_text()}")

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
