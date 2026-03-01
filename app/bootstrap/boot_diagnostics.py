from __future__ import annotations

import faulthandler
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import TextIO

from app.bootstrap.logging import write_crash_log

BOOT_TRACE_LOG_NAME = "boot_trace.log"
FAULT_HANDLER_LOG_NAME = "faulthandler.log"

_boot_trace_stream: TextIO | None = None
_faulthandler_stream: TextIO | None = None
_current_log_dir: Path | None = None



def _close_stream(stream: TextIO | None) -> None:
    if stream is None or stream.closed:
        return
    stream.close()

def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_boot_line(message: str) -> None:
    if _boot_trace_stream is None:
        return
    _boot_trace_stream.write(f"{_timestamp_utc()} {message}\n")
    _boot_trace_stream.flush()


def marcar_stage(stage: str) -> None:
    _write_boot_line(f"BOOT_STAGE={stage}")


def _write_exception_trace(
    source: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> None:
    _write_boot_line(
        f"UNHANDLED_EXCEPTION source={source} type={exc_type.__name__} message={exc_value}"
    )
    formatted_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)).rstrip()
    _write_boot_line(f"TRACEBACK_BEGIN source={source}")
    for line in formatted_traceback.splitlines():
        _write_boot_line(f"TRACE {line}")
    _write_boot_line(f"TRACEBACK_END source={source}")


def _write_crash_log_safe(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
    log_dir: Path,
) -> None:
    try:
        write_crash_log(exc_type, exc_value, exc_traceback, log_dir)
    except Exception as exc:  # noqa: BLE001
        _write_boot_line(f"CRASH_LOG_WRITE_FAILED type={type(exc).__name__} message={exc}")


def _build_sys_excepthook(log_dir: Path):
    def _sys_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType,
    ) -> None:
        _write_exception_trace("sys", exc_type, exc_value, exc_traceback)
        _write_crash_log_safe(exc_type, exc_value, exc_traceback, log_dir)

    return _sys_excepthook


def _build_threading_excepthook(log_dir: Path):
    def _threading_excepthook(args: threading.ExceptHookArgs) -> None:
        _write_exception_trace("threading", args.exc_type, args.exc_value, args.exc_traceback)
        _write_crash_log_safe(args.exc_type, args.exc_value, args.exc_traceback, log_dir)

    return _threading_excepthook


def init_boot_diagnostics(ruta_logs: Path) -> None:
    global _boot_trace_stream, _current_log_dir, _faulthandler_stream

    ruta_logs.mkdir(parents=True, exist_ok=True)

    if _current_log_dir != ruta_logs:
        _close_stream(_boot_trace_stream)
        _close_stream(_faulthandler_stream)
        _boot_trace_stream = None
        _faulthandler_stream = None

    _current_log_dir = ruta_logs

    if _boot_trace_stream is None or _boot_trace_stream.closed:
        _boot_trace_stream = (ruta_logs / BOOT_TRACE_LOG_NAME).open("a", encoding="utf-8")

    if _faulthandler_stream is None or _faulthandler_stream.closed:
        _faulthandler_stream = (ruta_logs / FAULT_HANDLER_LOG_NAME).open("a", encoding="utf-8")

    marcar_stage("boot_diagnostics_initialized")

    if not faulthandler.is_enabled():
        faulthandler.enable(file=_faulthandler_stream, all_threads=True)
        marcar_stage("faulthandler_enabled")
    else:
        marcar_stage("faulthandler_already_enabled")

    sys.excepthook = _build_sys_excepthook(ruta_logs)
    threading.excepthook = _build_threading_excepthook(ruta_logs)
    marcar_stage("exception_hooks_installed")
