from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain.sheets_errors import SheetsPermissionError
from app.ui.controllers import sync_controller as module
from app.ui.controllers.sync_controller import SyncController, _SyncWorker


class _FakeSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)


class _FakeThread:
    def __init__(self) -> None:
        self.started = _FakeSignal()
        self.finished = _FakeSignal()
        self.started_callbacks = self.started.callbacks
        self.finished_callbacks = self.finished.callbacks
        self.started_flag = False

    def quit(self) -> None:
        return None

    def deleteLater(self) -> None:
        return None

    def start(self) -> None:
        self.started_flag = True


class _FakeWorker:
    def __init__(self, operation, _correlation_id: str, _operation_name: str) -> None:
        self.operation = operation
        self.finished = _FakeSignal()
        self.failed = _FakeSignal()

    def moveToThread(self, _thread) -> None:
        return None

    def run(self):
        return self.operation()

    def deleteLater(self) -> None:
        return None


def _build_window() -> SimpleNamespace:
    return SimpleNamespace(
        _sync_in_progress=False,
        _sync_service=SimpleNamespace(is_configured=Mock(return_value=True), sync_bidirectional=Mock(return_value={"ok": True})),
        _set_sync_in_progress=Mock(),
        _on_sync_finished=Mock(),
        _on_sync_failed=Mock(),
        toast=Mock(),
    )


@pytest.mark.headless_safe
def test_start_sync_success(monkeypatch) -> None:
    window = _build_window()
    monkeypatch.setattr(module, "QThread", _FakeThread)
    monkeypatch.setattr(module, "_SyncWorker", _FakeWorker)

    controller = SyncController(window)
    controller.on_sync()

    window._set_sync_in_progress.assert_called_once_with(True)
    assert isinstance(window._sync_thread, _FakeThread)
    assert window._sync_thread.started_flag is True


@pytest.mark.headless_safe
def test_start_sync_sheets_permission_error() -> None:
    error = SheetsPermissionError("Sin permisos")
    failed_emits = []

    worker = _SyncWorker(lambda: (_ for _ in ()).throw(error), "corr-1", "sync_bidirectional")
    worker.failed.connect(lambda payload: failed_emits.append(payload))

    worker.run()

    assert len(failed_emits) == 1
    assert failed_emits[0]["error"] is error
