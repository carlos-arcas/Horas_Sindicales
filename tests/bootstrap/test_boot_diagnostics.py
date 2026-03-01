from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.bootstrap import boot_diagnostics


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_init_boot_diagnostics_crea_logs_y_hooks(monkeypatch, tmp_path) -> None:
    calls: dict[str, object] = {}

    def _fake_enable(*, file, all_threads):  # noqa: ANN001
        calls["file"] = file
        calls["all_threads"] = all_threads

    monkeypatch.setattr(boot_diagnostics.faulthandler, "is_enabled", lambda: False)
    monkeypatch.setattr(boot_diagnostics.faulthandler, "enable", _fake_enable)

    boot_diagnostics.init_boot_diagnostics(tmp_path)

    boot_trace = tmp_path / boot_diagnostics.BOOT_TRACE_LOG_NAME
    assert boot_trace.exists()
    contenido = _read(boot_trace)
    assert "BOOT_STAGE=boot_diagnostics_initialized" in contenido
    assert "BOOT_STAGE=faulthandler_enabled" in contenido
    assert "BOOT_STAGE=exception_hooks_installed" in contenido
    assert callable(boot_diagnostics.sys.excepthook)
    assert callable(boot_diagnostics.threading.excepthook)
    assert calls["all_threads"] is True


def test_sys_excepthook_registra_traza_y_crash_log(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(boot_diagnostics.faulthandler, "is_enabled", lambda: True)

    crash_calls: dict[str, object] = {}

    def _fake_write_crash_log(exc_type, exc_value, exc_traceback, log_dir) -> None:  # noqa: ANN001
        crash_calls["exc_type"] = exc_type
        crash_calls["exc_value"] = exc_value
        crash_calls["exc_traceback"] = exc_traceback
        crash_calls["log_dir"] = log_dir

    monkeypatch.setattr(boot_diagnostics, "write_crash_log", _fake_write_crash_log)

    boot_diagnostics.init_boot_diagnostics(tmp_path)

    try:
        raise RuntimeError("fallo sys")
    except RuntimeError as exc:
        boot_diagnostics.sys.excepthook(RuntimeError, exc, exc.__traceback__)

    assert crash_calls["exc_type"] is RuntimeError
    assert str(crash_calls["exc_value"]) == "fallo sys"
    assert crash_calls["log_dir"] == tmp_path
    assert "UNHANDLED_EXCEPTION source=sys" in _read(tmp_path / boot_diagnostics.BOOT_TRACE_LOG_NAME)


def test_threading_excepthook_registra_traza(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(boot_diagnostics.faulthandler, "is_enabled", lambda: True)

    captured: dict[str, object] = {}

    def _fake_write_crash_log(exc_type, exc_value, exc_traceback, log_dir) -> None:  # noqa: ANN001
        captured["exc_type"] = exc_type
        captured["exc_value"] = exc_value
        captured["traceback"] = exc_traceback
        captured["log_dir"] = log_dir

    monkeypatch.setattr(boot_diagnostics, "write_crash_log", _fake_write_crash_log)

    boot_diagnostics.init_boot_diagnostics(tmp_path)

    try:
        raise ValueError("fallo thread")
    except ValueError as exc:
        args = SimpleNamespace(exc_type=ValueError, exc_value=exc, exc_traceback=exc.__traceback__)
        boot_diagnostics.threading.excepthook(args)

    assert captured["exc_type"] is ValueError
    assert str(captured["exc_value"]) == "fallo thread"
    assert captured["log_dir"] == tmp_path
    assert "UNHANDLED_EXCEPTION source=threading" in _read(tmp_path / boot_diagnostics.BOOT_TRACE_LOG_NAME)
