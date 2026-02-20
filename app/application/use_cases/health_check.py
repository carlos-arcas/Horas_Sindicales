from __future__ import annotations

from datetime import datetime

from app.domain.ports import LocalDbProbe, SheetsConnectivityProbe, SheetsSchemaProbe
from app.domain.sync_models import HealthCheckItem, HealthReport


class HealthCheckUseCase:
    def __init__(
        self,
        schema_probe: SheetsSchemaProbe,
        connectivity_probe: SheetsConnectivityProbe,
        local_db_probe: LocalDbProbe,
    ) -> None:
        self._schema_probe = schema_probe
        self._connectivity_probe = connectivity_probe
        self._local_db_probe = local_db_probe

    def run(self) -> HealthReport:
        checks: list[HealthCheckItem] = []

        schema_checks = self._schema_probe.check()
        checks.extend(self._build_checks("Configuración", schema_checks))

        internet_ok, api_reachable, latency_ms, latency_message = self._connectivity_probe.check()
        checks.append(
            HealthCheckItem(
                key="internet_access",
                status="OK" if internet_ok else "WARN",
                message="Conectividad a internet disponible." if internet_ok else "No se detecta acceso a internet.",
                action_id="open_network_help",
                category="Conectividad",
            )
        )
        checks.append(
            HealthCheckItem(
                key="api_reachable",
                status="OK" if api_reachable else "ERROR",
                message="API de Google Sheets alcanzable." if api_reachable else "No se puede alcanzar la API de Google Sheets.",
                action_id="open_sync_settings",
                category="Conectividad",
            )
        )
        checks.append(
            HealthCheckItem(
                key="api_latency",
                status="OK" if latency_ms is not None and latency_ms < 1500 else "WARN",
                message=latency_message,
                action_id="open_sync_settings",
                category="Conectividad",
            )
        )

        local_checks = self._local_db_probe.check()
        checks.extend(self._build_checks("Integridad local", local_checks))
        return HealthReport(generated_at=datetime.now().isoformat(), checks=tuple(checks))

    @staticmethod
    def _build_checks(category: str, checks: dict[str, tuple[bool, str, str]]) -> list[HealthCheckItem]:
        mapped: list[HealthCheckItem] = []
        for key, (ok, message, action_id) in checks.items():
            mapped.append(
                HealthCheckItem(
                    key=key,
                    status="OK" if ok else "ERROR",
                    message=message,
                    action_id=action_id,
                    category=category,
                )
            )
        return mapped
