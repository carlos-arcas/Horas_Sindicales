from __future__ import annotations

from collections.abc import Callable

import pytest

qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
qt_core = pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
QApplication = getattr(qt_widgets, "QApplication", None)
QTabWidget = getattr(qt_widgets, "QTabWidget", None)
if not hasattr(qt_widgets, "QCheckBox"):
    pytest.skip(
        "PySide6 incompleto en entorno actual para tests UI de MainWindow",
        allow_module_level=True,
    )

from app.ui.vistas import main_window_vista


class NoOpService:
    def __getattr__(self, _name: str) -> Callable[..., list[object]]:
        return lambda *_args, **_kwargs: []


class FakeSyncService(NoOpService):
    def is_configured(self) -> bool:
        return True


def build_app():
    if QApplication is None or not hasattr(QApplication, "instance"):
        pytest.fail(
            "PySide6 real requerido en tests/ui: QApplication.instance no disponible (stub detectado)"
        )
    return QApplication.instance() or QApplication([])


def _noop_method(method_name: str) -> Callable[..., object]:
    if method_name in {"_sync_source_text", "_sync_scope_text"}:
        return lambda self: "stub"
    if method_name == "_load_personas":
        return lambda self, select_id=None: None
    return lambda self, *_args, **_kwargs: None


def _patch_hook_if_exists(monkeypatch: pytest.MonkeyPatch, method_name: str) -> None:
    method = getattr(main_window_vista.MainWindow, method_name, None)
    if callable(method):
        monkeypatch.setattr(
            main_window_vista.MainWindow, method_name, _noop_method(method_name)
        )


def build_window(monkeypatch: pytest.MonkeyPatch, **deps):
    hooks = (
        "_load_personas",
        "_reload_pending_views",
        "_update_global_context",
        "_refresh_last_sync_label",
        "_update_sync_button_state",
        "_update_conflicts_reminder",
        "_refresh_health_and_alerts",
        "_sync_source_text",
        "_sync_scope_text",
    )
    for hook in hooks:
        _patch_hook_if_exists(monkeypatch, hook)

    resolved_deps = {
        "persona_use_cases": deps.get("persona_use_cases", NoOpService()),
        "solicitud_use_cases": deps.get("solicitud_use_cases", NoOpService()),
        "grupo_use_cases": deps.get("grupo_use_cases", NoOpService()),
        "sheets_service": deps.get("sheets_service", NoOpService()),
        "sync_sheets_use_case": deps.get("sync_sheets_use_case", FakeSyncService()),
        "conflicts_service": deps.get("conflicts_service", NoOpService()),
        "health_check_use_case": deps.get("health_check_use_case"),
        "alert_engine": deps.get("alert_engine"),
        "proveedor_ui_solo_lectura": deps.get(
            "proveedor_ui_solo_lectura", lambda: False
        ),
    }
    return main_window_vista.MainWindow(**resolved_deps)


def pump_events(n: int = 3) -> None:
    for _ in range(max(n, 0)):
        qt_core.QCoreApplication.processEvents()


def close_window(window) -> None:
    if window is None:
        return
    window.close()
    pump_events(2)


__all__ = [
    "NoOpService",
    "FakeSyncService",
    "QTabWidget",
    "build_app",
    "build_window",
    "close_window",
    "pump_events",
]
