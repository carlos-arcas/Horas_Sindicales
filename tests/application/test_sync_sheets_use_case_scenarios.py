from __future__ import annotations

import pytest

from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.core.errors import ValidationError
from app.domain.sheets_errors import (
    SheetsCredentialsError,
    SheetsPermissionError,
    SheetsRateLimitError,
)
from app.domain.sync_models import SyncSummary


class FakeSheetsSyncPort:
    def __init__(self) -> None:
        self.pull_result: SyncSummary | Exception = SyncSummary(0, 0, 0, 0)
        self.push_result: SyncSummary | Exception = SyncSummary(0, 0, 0, 0)
        self.sync_result: SyncSummary | Exception = SyncSummary(0, 0, 0, 0)
        self.configured = True
        self.last_sync_at: str | None = "2025-01-01T10:00:00Z"
        self.config_values: list[tuple[str, str]] = []
        self.pdf_logs: list[tuple[int, list[str], str | None]] = []
        self.calls: list[str] = []

    def _resolve(self, value: SyncSummary | Exception) -> SyncSummary:
        if isinstance(value, Exception):
            raise value
        return value

    def pull(self) -> SyncSummary:
        self.calls.append("pull")
        return self._resolve(self.pull_result)

    def push(self) -> SyncSummary:
        self.calls.append("push")
        return self._resolve(self.push_result)

    def sync(self) -> SyncSummary:
        self.calls.append("sync")
        return self._resolve(self.sync_result)

    def sync_bidirectional(self) -> SyncSummary:
        self.calls.append("sync_bidirectional")
        return self._resolve(self.sync_result)

    def is_configured(self) -> bool:
        self.calls.append("is_configured")
        return self.configured

    def get_last_sync_at(self) -> str | None:
        self.calls.append("get_last_sync_at")
        return self.last_sync_at

    def store_sync_config_value(self, key: str, value: str) -> None:
        self.calls.append("store_sync_config_value")
        if not key:
            raise ValidationError("sync config key vacío")
        self.config_values.append((key, value))

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        self.calls.append("register_pdf_log")
        if persona_id <= 0:
            raise ValidationError("persona_id inválido")
        self.pdf_logs.append((persona_id, fechas, pdf_hash))


@pytest.fixture
def fake_port() -> FakeSheetsSyncPort:
    return FakeSheetsSyncPort()


def test_sync_happy_path_without_conflicts(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.sync_result = SyncSummary(downloaded=4, uploaded=7, conflicts=0, omitted_duplicates=1)
    use_case = SyncSheetsUseCase(fake_port)

    result = use_case.sync_bidirectional()

    assert result == SyncSummary(downloaded=4, uploaded=7, conflicts=0, omitted_duplicates=1)
    assert fake_port.calls == ["sync_bidirectional"]


def test_sync_returns_conflict_summary_when_conflicts_exist(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.sync_result = SyncSummary(downloaded=2, uploaded=2, conflicts=3, omitted_duplicates=0)
    use_case = SyncSheetsUseCase(fake_port)

    result = use_case.sync()

    assert result.conflicts == 3
    assert result.downloaded == 2
    assert fake_port.calls == ["sync_bidirectional"]


def test_pull_propagates_rate_limit_error(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.pull_result = SheetsRateLimitError("Límite alcanzado")
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(SheetsRateLimitError, match="Límite alcanzado"):
        use_case.pull()

    assert fake_port.calls == ["pull"]


def test_push_propagates_permanent_credentials_error(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.push_result = SheetsCredentialsError("Credenciales inválidas")
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(SheetsCredentialsError, match="Credenciales inválidas"):
        use_case.push()

    assert fake_port.calls == ["push"]


def test_sync_propagates_permission_error_with_consistent_message(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.sync_result = SheetsPermissionError("Sin permisos sobre la hoja")
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(SheetsPermissionError, match="Sin permisos"):
        use_case.sync_bidirectional()

    assert fake_port.calls == ["sync_bidirectional"]


def test_cancellation_error_is_not_swallowed(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.sync_result = RuntimeError("sync cancelada por usuario")
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(RuntimeError, match="cancelada"):
        use_case.sync_bidirectional()

    assert fake_port.calls == ["sync_bidirectional"]


def test_is_configured_delegates_to_port(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.configured = False
    use_case = SyncSheetsUseCase(fake_port)

    assert use_case.is_configured() is False
    assert fake_port.calls == ["is_configured"]


def test_get_last_sync_at_returns_port_value(fake_port: FakeSheetsSyncPort) -> None:
    fake_port.last_sync_at = "2026-02-10T09:00:00Z"
    use_case = SyncSheetsUseCase(fake_port)

    result = use_case.get_last_sync_at()

    assert result == "2026-02-10T09:00:00Z"
    assert fake_port.calls == ["get_last_sync_at"]


def test_store_sync_config_value_rejects_invalid_input(fake_port: FakeSheetsSyncPort) -> None:
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(ValidationError, match="key vacío"):
        use_case.store_sync_config_value("", "123")

    assert fake_port.config_values == []
    assert fake_port.calls == ["store_sync_config_value"]


def test_register_pdf_log_stores_values_when_valid(fake_port: FakeSheetsSyncPort) -> None:
    use_case = SyncSheetsUseCase(fake_port)

    use_case.register_pdf_log(10, ["2026-02-01", "2026-02-02"], "abc")

    assert fake_port.pdf_logs == [(10, ["2026-02-01", "2026-02-02"], "abc")]
    assert fake_port.calls == ["register_pdf_log"]


def test_register_pdf_log_rejects_invalid_persona_id(fake_port: FakeSheetsSyncPort) -> None:
    use_case = SyncSheetsUseCase(fake_port)

    with pytest.raises(ValidationError, match="persona_id inválido"):
        use_case.register_pdf_log(0, ["2026-02-01"], None)

    assert fake_port.pdf_logs == []
    assert fake_port.calls == ["register_pdf_log"]
