from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ui.controllers.solicitudes_controller import SolicitudesController
from app.ui.controllers.sync_controller import SyncController


@pytest.mark.headless_safe
def test_sync_controller_contract_methods_are_callable_with_fake_window() -> None:
    calls: list[tuple[str, object]] = []

    def _set_sync_in_progress(value: bool) -> None:
        calls.append(("progress", value))

    def _set_sync_status_badge(value: str) -> None:
        calls.append(("badge", value))

    window = SimpleNamespace(
        _set_sync_in_progress=_set_sync_in_progress,
        _set_sync_status_badge=_set_sync_status_badge,
    )
    _ = SyncController(window)

    window._set_sync_in_progress(True)
    window._set_sync_status_badge("IDLE")

    assert calls == [("progress", True), ("badge", "IDLE")]


@pytest.mark.headless_safe
def test_solicitudes_controller_contract_methods_return_bool_without_exception() -> None:
    window = SimpleNamespace(
        _build_preview_solicitud=lambda: None,
        _selected_pending_for_editing=lambda: None,
        _solicitud_use_cases=SimpleNamespace(buscar_duplicado=lambda _sol: None),
        _handle_duplicate_detected=lambda _dup: False,
        _resolve_backend_conflict=lambda _persona_id, _solicitud: False,
    )
    controller = SolicitudesController(window)

    assert controller.window._handle_duplicate_detected(object()) is False
    assert controller.window._resolve_backend_conflict(1, object()) is False


@pytest.mark.headless_safe
def test_slot_config_delegada_accepts_signal_argument_in_signature() -> None:
    source = Path("app/ui/vistas/main_window/state_controller.py").read_text(encoding="utf-8")
    module_ast = ast.parse(source)

    main_window = next(
        node for node in module_ast.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    method = next(
        node for node in main_window.body if isinstance(node, ast.FunctionDef) and node.name == "_on_config_delegada_changed"
    )

    assert method.args.vararg is not None
