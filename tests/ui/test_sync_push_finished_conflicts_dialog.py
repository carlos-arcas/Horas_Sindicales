from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.domain.sync_models import SyncSummary
from app.ui.vistas.main_window import acciones_sincronizacion_resultados as module


def _build_window() -> SimpleNamespace:
    return SimpleNamespace(
        _conflicts_service=Mock(),
        _update_solicitudes_status_panel=Mock(),
        _refresh_last_sync_label=Mock(),
    )


def test_on_push_finished_no_abre_conflicts_dialog_con_solo_errores(monkeypatch) -> None:
    exec_mock = Mock()
    monkeypatch.setattr(module, "set_sync_in_progress", Mock())
    monkeypatch.setattr(module, "update_sync_button_state", Mock())
    monkeypatch.setattr(
        module,
        "ConflictsDialog",
        lambda *_args: SimpleNamespace(exec=exec_mock),
    )
    monkeypatch.setattr(module.dialogos_sincronizacion, "show_sync_summary_dialog", Mock())
    monkeypatch.setattr(module, "texto_interfaz", lambda key: key)

    module.on_push_finished(_build_window(), SyncSummary(errors=1, conflicts_detected=0))

    exec_mock.assert_not_called()


def test_on_push_finished_abre_conflicts_dialog_con_conflictos_reales(monkeypatch) -> None:
    exec_mock = Mock()
    monkeypatch.setattr(module, "set_sync_in_progress", Mock())
    monkeypatch.setattr(module, "update_sync_button_state", Mock())
    monkeypatch.setattr(
        module,
        "ConflictsDialog",
        lambda *_args: SimpleNamespace(exec=exec_mock),
    )
    monkeypatch.setattr(module.dialogos_sincronizacion, "show_sync_summary_dialog", Mock())
    monkeypatch.setattr(module, "texto_interfaz", lambda key: key)

    module.on_push_finished(_build_window(), SyncSummary(errors=1, conflicts_detected=2))

    exec_mock.assert_called_once_with()
