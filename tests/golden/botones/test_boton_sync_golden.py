from __future__ import annotations

from pathlib import Path

from tests.utilidades.event_recorder import EventRecorder
from tests.golden.botones._helpers import FakeToast, assert_matches_golden, install_pyside6_stubs


class _FakeSyncService:
    def is_configured(self) -> bool:
        return True

    def sync_bidirectional(self) -> dict[str, str]:
        return {"status": "ok"}


class _FakeWindow:
    def __init__(self, recorder: EventRecorder) -> None:
        self._sync_service = _FakeSyncService()
        self._sync_in_progress = False
        self._sync_operation_context = None
        self.toast = FakeToast(recorder)
        self._recorder = recorder

    def _set_sync_in_progress(self, value: bool) -> None:
        self._sync_in_progress = value
        self._recorder.record("estado_ui_cambiado", {"clave": "sync_in_progress", "valor": value})

    def _on_sync_finished(self, _result: object) -> None:
        self._recorder.record("use_case_llamado", {"nombre": "sync_bidirectional", "payload_minimo": {"status": "ok"}})

    def _on_sync_failed(self, _payload: object) -> None:
        raise AssertionError("No debería fallar en flujo determinista")


def test_boton_sync_golden_snapshot() -> None:
    install_pyside6_stubs()

    from app.ui.controllers.sync_controller import SyncController

    recorder = EventRecorder()
    window = _FakeWindow(recorder)
    controller = SyncController(window)

    recorder.record("click_boton", {"nombre": "Sync"})
    controller.on_sync()

    assert_matches_golden(Path(__file__), "sync", recorder.to_json())
