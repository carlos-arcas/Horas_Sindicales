from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
import time
from typing import Callable, Literal

from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.domain.sync_models import SyncSummary

logger = logging.getLogger(__name__)

SyncOperation = Literal["pull", "push", "sync"]


class SyncCancelledError(Exception):
    """Error lanzado cuando una sincronización se cancela explícitamente."""


class CancellationToken:
    """Token cooperativo para cancelación de sincronizaciones."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0


@dataclass(frozen=True)
class SyncOptions:
    operation: SyncOperation = "sync"
    timeout_seconds: float = 30.0
    dry_run: bool = False
    check_schema: bool = True
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    cancellation_token: CancellationToken | None = None


@dataclass(frozen=True)
class SyncReport:
    operation: SyncOperation
    dry_run: bool
    attempts: int
    creations: int
    updates: int
    omitted_duplicates: int
    errors: list[str]
    schema_actions: list[str]
    duration_seconds: float


class StructuredFileLogger:
    """Logger estructurado JSON Lines para auditoría de sync."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **payload: object) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        with self._lock, self._path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


class GoogleSheetsSyncModule:
    """Orquestador avanzado de sincronización con reintentos y reporte final."""

    def __init__(
        self,
        sync_use_case: SyncSheetsUseCase,
        *,
        schema_checker: Callable[[], list[str]] | None = None,
        structured_logger: StructuredFileLogger | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sync_use_case = sync_use_case
        self._schema_checker = schema_checker
        self._structured_logger = structured_logger
        self._sleeper = sleeper
        self._clock = clock

    def run(self, options: SyncOptions) -> SyncReport:
        started = self._clock()
        schema_actions: list[str] = []
        errors: list[str] = []
        attempts = 0

        self._log("sync_started", operation=options.operation, dry_run=options.dry_run)
        self._raise_if_cancelled(options.cancellation_token)

        if options.check_schema and self._schema_checker and not options.dry_run:
            schema_actions = self._schema_checker()
            self._log("schema_checked", actions=schema_actions)

        if options.dry_run:
            duration = self._clock() - started
            self._log("sync_dry_run", operation=options.operation, duration_seconds=duration)
            return SyncReport(
                operation=options.operation,
                dry_run=True,
                attempts=0,
                creations=0,
                updates=0,
                omitted_duplicates=0,
                errors=[],
                schema_actions=schema_actions,
                duration_seconds=duration,
            )

        retry = options.retry_policy
        while attempts < retry.max_attempts:
            attempts += 1
            self._raise_if_cancelled(options.cancellation_token)
            try:
                summary = self._run_with_timeout(options.operation, options.timeout_seconds)
                report = self._summary_to_report(
                    options=options,
                    summary=summary,
                    attempts=attempts,
                    schema_actions=schema_actions,
                    duration=self._clock() - started,
                )
                self._log("sync_succeeded", attempts=attempts, report=report.__dict__)
                return report
            except SyncCancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                self._log("sync_attempt_failed", attempt=attempts, error=str(exc))
                if attempts >= retry.max_attempts or not self._is_retryable(exc):
                    break
                backoff = retry.initial_backoff_seconds * (retry.backoff_multiplier ** (attempts - 1))
                self._log("sync_retry_scheduled", attempt=attempts, backoff_seconds=backoff)
                self._sleep_with_cancellation(backoff, options.cancellation_token)

        duration = self._clock() - started
        self._log("sync_failed", attempts=attempts, errors=errors, duration_seconds=duration)
        return SyncReport(
            operation=options.operation,
            dry_run=False,
            attempts=attempts,
            creations=0,
            updates=0,
            omitted_duplicates=0,
            errors=errors,
            schema_actions=schema_actions,
            duration_seconds=duration,
        )

    def _run_with_timeout(self, operation: SyncOperation, timeout_seconds: float) -> SyncSummary:
        self._log("sync_attempt_started", operation=operation, timeout_seconds=timeout_seconds)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._dispatch_operation, operation)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                future.cancel()
                raise TimeoutError(f"Timeout en sincronización '{operation}' tras {timeout_seconds} segundos") from exc

    def _dispatch_operation(self, operation: SyncOperation) -> SyncSummary:
        if operation == "pull":
            return self._sync_use_case.pull()
        if operation == "push":
            return self._sync_use_case.push()
        return self._sync_use_case.sync()

    def _summary_to_report(
        self,
        *,
        options: SyncOptions,
        summary: SyncSummary,
        attempts: int,
        schema_actions: list[str],
        duration: float,
    ) -> SyncReport:
        is_initial_sync = self._sync_use_case.get_last_sync_at() is None
        total_changes = summary.downloaded + summary.uploaded
        creations = total_changes if is_initial_sync else 0
        updates = 0 if is_initial_sync else total_changes
        return SyncReport(
            operation=options.operation,
            dry_run=False,
            attempts=attempts,
            creations=creations,
            updates=updates,
            omitted_duplicates=summary.omitted_duplicates,
            errors=[],
            schema_actions=schema_actions,
            duration_seconds=duration,
        )

    def _is_retryable(self, exc: Exception) -> bool:
        transient_exceptions = (TimeoutError, ConnectionError, OSError)
        return isinstance(exc, transient_exceptions)

    def _sleep_with_cancellation(self, seconds: float, token: CancellationToken | None) -> None:
        remaining = seconds
        while remaining > 0:
            self._raise_if_cancelled(token)
            step = min(0.1, remaining)
            self._sleeper(step)
            remaining -= step

    def _raise_if_cancelled(self, token: CancellationToken | None) -> None:
        if token and token.is_cancelled():
            self._log("sync_cancelled")
            raise SyncCancelledError("Sincronización cancelada por el usuario")

    def _log(self, event: str, **payload: object) -> None:
        logger.info("sync_event=%s payload=%s", event, payload)
        if self._structured_logger:
            self._structured_logger.log(event, **payload)
