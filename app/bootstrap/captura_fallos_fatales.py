from __future__ import annotations

import atexit
import faulthandler
import logging
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import TextIO

LOGGER = logging.getLogger(__name__)
_CRASH_LOG = "crashes.log"
_SEGUIMIENTO_LOG = "seguimiento.log"

_crash_stream: TextIO | None = None
_seguimiento_path: Path | None = None
_stderr_original: TextIO | None = None
_stdout_original: TextIO | None = None


class _TeeStream:
    def __init__(self, *streams: TextIO) -> None:
        self._streams = tuple(stream for stream in streams if stream is not None)

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def _cerrar_stream(stream: TextIO | None) -> None:
    if stream is None or stream.closed:
        return
    stream.flush()
    stream.close()



def _escribir_crash(texto: str) -> None:
    if _crash_stream is None:
        return
    _crash_stream.write(texto)
    _crash_stream.flush()



def _escribir_seguimiento(nombre: str) -> None:
    if _seguimiento_path is None:
        return
    with _seguimiento_path.open("a", encoding="utf-8") as stream:
        stream.write(f"{_utc_now()} BOOT_STAGE={nombre}\n")



def _formatear_trace(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> str:
    return "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))



def _instalar_sys_excepthook() -> None:
    def _hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
        LOGGER.critical("EXCEPCION_NO_CONTROLADA", exc_info=(exc_type, exc_value, exc_traceback))
        _escribir_crash(_formatear_trace(exc_type, exc_value, exc_traceback))

    sys.excepthook = _hook



def _instalar_threading_excepthook() -> None:
    def _hook(args: threading.ExceptHookArgs) -> None:
        LOGGER.critical(
            "EXCEPCION_NO_CONTROLADA_EN_HILO",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        _escribir_crash(_formatear_trace(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = _hook



def _registrar_atexit() -> None:
    def _flush_final() -> None:
        for stream in (_crash_stream, _stderr_original, _stdout_original):
            if stream is None:
                continue
            try:
                stream.flush()
            except Exception:
                continue

    atexit.register(_flush_final)



def iniciar_captura_fallos_fatales(*, log_dir: Path, sobrescribir: bool = True) -> None:
    global _crash_stream, _seguimiento_path, _stderr_original, _stdout_original

    log_dir.mkdir(parents=True, exist_ok=True)
    crash_path = log_dir / _CRASH_LOG
    _seguimiento_path = log_dir / _SEGUIMIENTO_LOG

    if sobrescribir:
        crash_path.write_text("", encoding="utf-8")
        _seguimiento_path.write_text("", encoding="utf-8")

    _cerrar_stream(_crash_stream)
    _crash_stream = crash_path.open("a", encoding="utf-8", buffering=1)

    if not faulthandler.is_enabled():
        faulthandler.enable(file=_crash_stream, all_threads=True)

    if _stderr_original is None:
        _stderr_original = sys.stderr
    sys.stderr = _TeeStream(_stderr_original, _crash_stream)

    if _stdout_original is None:
        _stdout_original = sys.stdout
    sys.stdout = _TeeStream(_stdout_original, _crash_stream)

    _instalar_sys_excepthook()
    _instalar_threading_excepthook()
    _registrar_atexit()



def marcar_stage(nombre: str) -> None:
    _escribir_seguimiento(nombre)
    LOGGER.info("BOOT_STAGE=%s", nombre)


# Verificación manual: lanzar la UI y revisar logs/crashes.log + logs/seguimiento.log tras un cierre inesperado.
