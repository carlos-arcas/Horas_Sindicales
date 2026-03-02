from __future__ import annotations

import warnings

import pytest

from app.ui.qt_compat import QApplication, QCheckBox

try:
    from app.ui.vistas.main_window.state_controller import MainWindow
except ImportError as exc:  # pragma: no cover - depende del entorno de Qt
    pytest.skip(f"Qt no disponible para este test: {exc}", allow_module_level=True)


class _SettingsFake:
    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def value(self, key: str, default: object) -> object:
        return self._values.get(key, default)


class _ControladorAyudaDummy:
    def __init__(self) -> None:
        self.show_help_toggle = QCheckBox()
        self._settings = _SettingsFake()
        self._help_toggle_conectado = False
        self.cambios: list[bool] = []

    def _on_help_toggle_changed(self, enabled: bool) -> None:
        self.cambios.append(bool(enabled))


def test_apply_help_preferences_no_emite_runtimewarning_al_desconectar_slot() -> None:
    app = QApplication.instance() or QApplication([])
    controlador = _ControladorAyudaDummy()

    MainWindow._apply_help_preferences(controlador)

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", RuntimeWarning)
        MainWindow._apply_help_preferences(controlador)

    assert app is not None
    assert controlador._help_toggle_conectado is True
    assert not [w for w in captured if "Failed to disconnect" in str(w.message)]
