from __future__ import annotations

from pathlib import Path

from app.application.sync import (
    CancellationToken,
    GoogleSheetsSyncModule,
    RetryPolicy,
    StructuredFileLogger,
    SyncOptions,
)
from app.application.sync_sheets_use_case import SyncSheetsUseCase


def run_sync(sync_use_case: SyncSheetsUseCase) -> None:
    token = CancellationToken()
    module = GoogleSheetsSyncModule(
        sync_use_case,
        structured_logger=StructuredFileLogger(Path("logs/sync.jsonl")),
    )

    options = SyncOptions(
        operation="sync",
        timeout_seconds=45,
        dry_run=False,
        check_schema=True,
        retry_policy=RetryPolicy(max_attempts=4, initial_backoff_seconds=1.0, backoff_multiplier=2.0),
        cancellation_token=token,
    )

    report = module.run(options)
    print(report)


if __name__ == "__main__":
    raise SystemExit("Ejemplo: inyecta un SyncSheetsUseCase real y llama a run_sync(sync_use_case)")
