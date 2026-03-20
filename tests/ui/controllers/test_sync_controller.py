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
        _sync_service=SimpleNamespace(
            is_configured=Mock(return_value=True),
            sync_bidirectional=Mock(return_value={"ok": True}),
            get_service_account_email=Mock(return_value="sync-bot@example.iam.gserviceaccount.com"),
        ),
        _set_sync_in_progress=Mock(),
        _on_sync_finished=Mock(),
        _on_sync_failed=Mock(),
        toast=Mock(),
    )


def _build_sync_report(errors: int = 0, conflicts: int = 0) -> SimpleNamespace:
    return SimpleNamespace(errors=errors, conflicts=conflicts)


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


@pytest.mark.headless_safe
def test_controller_handles_permission_error_without_propagating() -> None:
    window = _build_window()
    controller = SyncController(window)
    error = SheetsPermissionError("403", service_account_email="sync-bot@example.iam.gserviceaccount.com")

    controller._on_sync_failed({"error": error, "details": "trace"})

    window._on_sync_failed.assert_called_once()
    window.toast.warning.assert_called_once()
    toast_message = window.toast.warning.call_args.args[0]
    assert "sync-bot@example.iam.gserviceaccount.com" in toast_message


@pytest.mark.headless_safe
def test_on_context_changed_invalida_plan_pendiente_y_reporte_contextual() -> None:
    window = _build_window()
    window._pending_sync_plan = object()
    window._last_sync_report = _build_sync_report(errors=1, conflicts=1)
    window._active_sync_id = "sync-1"
    window._attempt_history = ("intento-1",)
    window._sync_attempts = [{"status": "ERROR"}]
    window._sync_operation_context = object()
    window.confirm_sync_button = Mock()
    window.retry_failed_button = Mock()
    window.sync_details_button = Mock()
    window.copy_sync_report_button = Mock()
    window._set_sync_status_badge = Mock()
    window.sync_panel_status = Mock()
    window._refresh_last_sync_label = Mock()
    window._refresh_health_and_alerts = Mock()
    window._conflicts_service = SimpleNamespace(count_conflicts=Mock(return_value=0))
    window.sync_button = Mock()
    window.review_conflicts_button = Mock()
    window.simulate_sync_button = Mock()

    controller = SyncController(window)
    controller.on_context_changed()

    assert window._pending_sync_plan is None
    assert window._last_sync_report is None
    assert window._active_sync_id is None
    assert window._attempt_history == ()
    assert window._sync_attempts == []
    assert window._sync_operation_context is None
    assert window.confirm_sync_button.setEnabled.call_args_list[-1] == ((False,), {})
    assert window.retry_failed_button.setEnabled.call_args_list[-1] == ((False,), {})
    assert window.sync_details_button.setEnabled.call_args_list[-1] == ((False,), {})
    assert window.copy_sync_report_button.setEnabled.call_args_list[-1] == ((False,), {})
    window._set_sync_status_badge.assert_called_once_with("IDLE")
    window._refresh_last_sync_label.assert_called_once_with()
    window._refresh_health_and_alerts.assert_called_once_with()


@pytest.mark.headless_safe
def test_on_context_changed_mantiene_estado_en_progreso_y_limpia_reporte_viejo() -> None:
    window = _build_window()
    window._sync_in_progress = True
    window._pending_sync_plan = object()
    window._last_sync_report = _build_sync_report(errors=1)
    window._sync_operation_context = object()
    window.confirm_sync_button = Mock()
    window.retry_failed_button = Mock()
    window.sync_details_button = Mock()
    window.copy_sync_report_button = Mock()
    window._set_sync_status_badge = Mock()
    window.sync_panel_status = Mock()
    window._refresh_last_sync_label = Mock()
    window._refresh_health_and_alerts = Mock()
    window._conflicts_service = SimpleNamespace(count_conflicts=Mock(return_value=0))
    window.sync_button = Mock()
    window.review_conflicts_button = Mock()
    window.simulate_sync_button = Mock()

    controller = SyncController(window)
    controller.on_context_changed()

    assert window._pending_sync_plan is None
    assert window._last_sync_report is None
    assert window._sync_operation_context is not None
    assert window.retry_failed_button.setEnabled.call_args_list[-1] == ((False,), {})
    assert window.sync_details_button.setEnabled.call_args_list[-1] == ((False,), {})
    assert window.copy_sync_report_button.setEnabled.call_args_list[-1] == ((False,), {})
    window._set_sync_status_badge.assert_not_called()
    window._refresh_last_sync_label.assert_not_called()
    window._refresh_health_and_alerts.assert_not_called()


@pytest.mark.headless_safe
def test_update_sync_button_state_habilita_acciones_con_reporte_vigente() -> None:
    window = _build_window()
    window._pending_sync_plan = None
    window._last_sync_report = _build_sync_report(errors=1, conflicts=0)
    window._conflicts_service = SimpleNamespace(count_conflicts=Mock(return_value=0))
    window.sync_button = Mock()
    window.review_conflicts_button = Mock()
    window.simulate_sync_button = Mock()
    window.confirm_sync_button = Mock()
    window.retry_failed_button = Mock()
    window.sync_details_button = Mock()
    window.copy_sync_report_button = Mock()

    controller = SyncController(window)
    controller.update_sync_button_state()

    assert window.retry_failed_button.setEnabled.call_args_list[-1] == ((True,), {})
    assert window.sync_details_button.setEnabled.call_args_list[-1] == ((True,), {})
    assert window.copy_sync_report_button.setEnabled.call_args_list[-1] == ((True,), {})


@pytest.mark.headless_safe
def test_finished_callback_tardio_no_reescribe_contexto_activo(monkeypatch) -> None:
    window = _build_window()
    window._pending_sync_plan = object()
    window._reload_pending_views = Mock()
    window._refresh_historico = Mock()
    window._refresh_saldos = Mock()
    window._update_global_context = Mock()
    window._conflicts_service = SimpleNamespace(count_conflicts=Mock(return_value=0))
    window.sync_button = Mock()
    window.review_conflicts_button = Mock()
    monkeypatch.setattr(module, 'resolve_active_delegada_id', lambda _window: 2)

    on_finished = Mock()
    controller = SyncController(window)
    controller._handle_operation_finished(
        {'ok': True},
        expected_persona_id=1,
        on_finished=on_finished,
        operation_name='sync_bidirectional',
    )

    on_finished.assert_not_called()
    window._set_sync_in_progress.assert_called_once_with(False)
    assert window._pending_sync_plan is None
    window._reload_pending_views.assert_called_once_with()
    window._refresh_historico.assert_called_once_with()
    window._refresh_saldos.assert_called_once_with()
    window._update_global_context.assert_called_once_with()


@pytest.mark.headless_safe
def test_failed_callback_tardio_no_reescribe_contexto_activo(monkeypatch) -> None:
    window = _build_window()
    window._pending_sync_plan = object()
    window._reload_pending_views = Mock()
    window._refresh_historico = Mock()
    window._refresh_saldos = Mock()
    window._update_global_context = Mock()
    window._conflicts_service = SimpleNamespace(count_conflicts=Mock(return_value=0))
    window.sync_button = Mock()
    window.review_conflicts_button = Mock()
    monkeypatch.setattr(module, 'resolve_active_delegada_id', lambda _window: 2)

    controller = SyncController(window)
    controller._handle_operation_failed(
        {'error': RuntimeError('boom')},
        expected_persona_id=1,
        operation_name='sync_bidirectional',
    )

    window._on_sync_failed.assert_not_called()
    window._set_sync_in_progress.assert_called_once_with(False)
    assert window._pending_sync_plan is None
