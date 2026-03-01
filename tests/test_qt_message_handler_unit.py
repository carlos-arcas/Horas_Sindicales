from __future__ import annotations

import logging

from app.ui import qt_message_handler


class _BootTraceWriterSpy:
    def __init__(self) -> None:
        self.stages: list[str] = []

    def marcar_stage(self, stage: str) -> None:
        self.stages.append(stage)


class _ContextoFalso:
    category = "qt.category"
    file = "widget.cpp"
    line = 123
    function = "crear_widget"


def test_procesar_mensaje_qt_registra_violacion_y_stage(caplog, monkeypatch) -> None:
    caplog.set_level(logging.DEBUG)
    writer = _BootTraceWriterSpy()
    monkeypatch.setattr(qt_message_handler, "_debe_fallar_ci", lambda: False)

    qt_message_handler._procesar_mensaje_qt(
        tipo_qt="QtWarningMsg",
        contexto=_ContextoFalso(),
        mensaje=qt_message_handler.MENSAJE_VIOLACION_THREAD_PARENT,
        logger=logging.getLogger("test.qt"),
        boot_trace_writer=writer,
    )

    assert writer.stages == ["QT_THREAD_PARENT_VIOLATION"]
    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert any(getattr(record, "extra", {}).get("qt", {}).get("thread_parent_violation") for record in caplog.records)


def test_procesar_mensaje_qt_no_violation_no_stage(caplog, monkeypatch) -> None:
    caplog.set_level(logging.DEBUG)
    writer = _BootTraceWriterSpy()
    monkeypatch.setattr(qt_message_handler, "_debe_fallar_ci", lambda: False)

    qt_message_handler._procesar_mensaje_qt(
        tipo_qt="QtDebugMsg",
        contexto=_ContextoFalso(),
        mensaje="debug de render",
        logger=logging.getLogger("test.qt"),
        boot_trace_writer=writer,
    )

    assert writer.stages == []
    assert any(record.levelno == logging.DEBUG for record in caplog.records)
