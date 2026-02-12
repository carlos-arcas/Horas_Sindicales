from __future__ import annotations

from pathlib import Path

import pytest

from app.application.sync import (
    CancellationToken,
    GoogleSheetsSyncModule,
    RetryPolicy,
    StructuredFileLogger,
    SyncCancelledError,
    SyncOptions,
)
from app.domain.sync_models import SyncSummary


class _FakeSyncUseCase:
    def __init__(self, outcomes: list[object], last_sync_at: str | None = "2025-01-01T00:00:00Z") -> None:
        self._outcomes = outcomes
        self._last_sync_at = last_sync_at

    def _next(self) -> SyncSummary:
        value = self._outcomes.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def pull(self) -> SyncSummary:
        return self._next()

    def push(self) -> SyncSummary:
        return self._next()

    def sync(self) -> SyncSummary:
        return self._next()

    def get_last_sync_at(self) -> str | None:
        return self._last_sync_at


def test_retry_with_exponential_backoff() -> None:
    sleep_calls: list[float] = []
    use_case = _FakeSyncUseCase(
        [
            ConnectionError("fallo 1"),
            TimeoutError("fallo 2"),
            SyncSummary(downloaded=2, uploaded=3, conflicts=0, omitted_duplicates=1),
        ]
    )

    module = GoogleSheetsSyncModule(use_case, sleeper=sleep_calls.append)
    report = module.run(
        SyncOptions(
            operation="sync",
            retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0.5, backoff_multiplier=2.0),
            timeout_seconds=1,
        )
    )

    assert report.errors == []
    assert report.attempts == 3
    assert report.updates == 5
    assert report.omitted_duplicates == 1
    assert sum(sleep_calls) == pytest.approx(1.5, abs=1e-6)
    assert max(sleep_calls) <= 0.1


def test_dry_run_does_not_execute_sync() -> None:
    use_case = _FakeSyncUseCase([SyncSummary(downloaded=9, uploaded=9, conflicts=0, omitted_duplicates=0)])
    module = GoogleSheetsSyncModule(use_case)

    report = module.run(SyncOptions(dry_run=True))

    assert report.dry_run is True
    assert report.attempts == 0
    assert report.creations == 0
    assert report.updates == 0


def test_cancellation_stops_execution() -> None:
    token = CancellationToken()
    token.cancel()
    use_case = _FakeSyncUseCase([SyncSummary(downloaded=1, uploaded=1, conflicts=0, omitted_duplicates=0)])
    module = GoogleSheetsSyncModule(use_case)

    with pytest.raises(SyncCancelledError):
        module.run(SyncOptions(cancellation_token=token))


def test_structured_file_logger_writes_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "sync.jsonl"
    logger = StructuredFileLogger(log_path)
    logger.log("sync_started", operation="sync", dry_run=False)

    content = log_path.read_text(encoding="utf-8")
    assert '"event": "sync_started"' in content
    assert '"operation": "sync"' in content
