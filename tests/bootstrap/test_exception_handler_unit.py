from __future__ import annotations

import types
from types import SimpleNamespace

from app.bootstrap import exception_handler


class _LoggerFake:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def critical(self, message: str, incident_id: str, *, exc_info, extra) -> None:  # noqa: ANN001
        self.calls.append(
            {
                "message": message,
                "incident_id": incident_id,
                "exc_info": exc_info,
                "extra": extra,
            }
        )


def test_manejar_excepcion_global_loguea_y_escribe_crash_log(monkeypatch) -> None:
    logger = _LoggerFake()
    captured: dict[str, object] = {}

    monkeypatch.setattr(exception_handler, "logging", SimpleNamespace(getLogger=lambda _name: logger))
    monkeypatch.setattr(exception_handler, "generar_id_incidente", lambda: "INC-TEST-123")
    monkeypatch.setattr(exception_handler, "_asegurar_correlation_id", lambda: "corr-001")
    monkeypatch.setattr(exception_handler, "resolve_log_dir", lambda: "/tmp/fake")

    def _fake_write_crash_log(exc_type, exc_value, exc_traceback, log_dir) -> None:  # noqa: ANN001
        captured["exc_type"] = exc_type
        captured["exc_value"] = exc_value
        captured["exc_traceback"] = exc_traceback
        captured["log_dir"] = log_dir

    monkeypatch.setattr(exception_handler, "write_crash_log", _fake_write_crash_log)

    try:
        raise ValueError("fallo esperado")
    except ValueError as exc:
        incident_id = exception_handler.manejar_excepcion_global(ValueError, exc, exc.__traceback__)

    assert incident_id == "INC-TEST-123"
    assert logger.calls and logger.calls[0]["extra"] == {"incident_id": "INC-TEST-123", "correlation_id": "corr-001"}
    assert captured["exc_type"] is ValueError
    assert str(captured["exc_value"]) == "fallo esperado"


def test_manejar_excepcion_global_usa_fallback_si_write_crash_log_falla(monkeypatch) -> None:
    logger = _LoggerFake()
    fallback_called: dict[str, object] = {}

    monkeypatch.setattr(exception_handler, "logging", SimpleNamespace(getLogger=lambda _name: logger))
    monkeypatch.setattr(exception_handler, "generar_id_incidente", lambda: "INC-TEST-456")
    monkeypatch.setattr(exception_handler, "_asegurar_correlation_id", lambda: "corr-999")
    monkeypatch.setattr(
        exception_handler,
        "write_crash_log",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("io error")),
    )

    def _fake_fallback(**kwargs) -> None:  # noqa: ANN003
        fallback_called.update(kwargs)

    monkeypatch.setattr(exception_handler, "_escribir_fallback_crash_log", _fake_fallback)

    try:
        raise RuntimeError("explota")
    except RuntimeError as exc:
        incident_id = exception_handler.manejar_excepcion_global(RuntimeError, exc, exc.__traceback__)

    assert incident_id == "INC-TEST-456"
    assert fallback_called["incident_id"] == "INC-TEST-456"
    assert fallback_called["correlation_id"] == "corr-999"
    assert fallback_called["exc_type"] is RuntimeError
    assert isinstance(fallback_called["exc_traceback"], types.TracebackType)
