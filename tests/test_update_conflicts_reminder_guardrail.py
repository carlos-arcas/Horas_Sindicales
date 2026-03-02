from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def _stub_module(name: str, **attrs) -> None:
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


class _Dummy:
    pass


def _prepare_import_stubs() -> dict[str, ModuleType | None]:
    originals: dict[str, ModuleType | None] = {}

    def _register(name: str, **attrs) -> None:
        if name not in originals:
            originals[name] = sys.modules.get(name)
        _stub_module(name, **attrs)

    _register("app.domain")
    _register("app.bootstrap")
    _register("app.ui.vistas.main_window")
    _register("app.ui.workers")

    _register("app.domain.sheets_errors", SheetsPermissionError=Exception)
    _register(
        "app.domain.sync_models",
        SyncAttemptReport=_Dummy,
        SyncExecutionPlan=_Dummy,
        SyncSummary=_Dummy,
    )
    _register("app.ui.dialogos_comunes")
    _register("app.ui.conflicts_dialog", ConflictsDialog=_Dummy)
    _register("app.ui.error_mapping", map_error_to_ui_message=lambda *_a, **_k: None)
    _register("app.ui.notification_service", OperationFeedback=_Dummy)
    _register(
        "app.ui.sync_reporting",
        build_config_incomplete_report=lambda *_a, **_k: None,
        build_failed_report=lambda *_a, **_k: None,
        build_simulation_report=lambda *_a, **_k: None,
        build_sync_report=lambda *_a, **_k: None,
    )
    _register("app.ui.vistas.main_window.dialogos_sincronizacion")
    _register("app.ui.vistas.main_window_helpers", show_sync_error_dialog_from_exception=lambda *_a, **_k: None)
    _register("app.ui.workers.sincronizacion_workers", PushWorker=_Dummy)
    _register("app.bootstrap.logging", log_operational_error=lambda *_a, **_k: None)
    return originals


def _load_module():
    originals = _prepare_import_stubs()
    ruta = Path("app/ui/vistas/main_window/acciones_sincronizacion_resultados.py")
    spec = importlib.util.spec_from_file_location("acciones_sincronizacion_resultados", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
    finally:
        for module_name, original in reversed(list(originals.items())):
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original
    return modulo


modulo = _load_module()


class _Label:
    def __init__(self) -> None:
        self.visible = None
        self.text = None

    def setVisible(self, value: bool) -> None:
        self.visible = value

    def setText(self, value: str) -> None:
        self.text = value


def _window(**overrides):
    base = {
        "conflicts_reminder_label": _Label(),
        "_i18n": object(),
        "_conflicts_service": SimpleNamespace(count_conflicts=lambda: 0),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_update_conflicts_reminder_early_return_sin_dependencias() -> None:
    ventana = _window(conflicts_reminder_label=None)

    modulo.update_conflicts_reminder(ventana)

    assert ventana.conflicts_reminder_label is None


def test_update_conflicts_reminder_normaliza_tipos_invalidos() -> None:
    label = _Label()
    ventana = _window(
        conflicts_reminder_label=label,
        _conflicts_service=SimpleNamespace(count_conflicts=lambda: "3"),
    )

    modulo.update_conflicts_reminder(ventana)

    assert label.visible is False
    assert label.text is None


def test_update_conflicts_reminder_captura_excepcion_y_loguea() -> None:
    label = _Label()
    logger_exception = Mock()
    ventana = _window(
        conflicts_reminder_label=label,
        _conflicts_service=SimpleNamespace(count_conflicts=lambda: 2),
    )
    label.setVisible = Mock(side_effect=RuntimeError("boom"))

    original = modulo.logger.exception
    modulo.logger.exception = logger_exception
    try:
        modulo.update_conflicts_reminder(ventana)
    finally:
        modulo.logger.exception = original

    logger_exception.assert_called_once_with("UI_UPDATE_CONFLICTS_REMINDER_FAILED")
