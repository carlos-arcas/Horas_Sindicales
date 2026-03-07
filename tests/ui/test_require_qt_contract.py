from __future__ import annotations

import pytest

from tests.ui import conftest as ui_conftest


def test_require_qt_skippea_en_modo_no_estricto_si_qt_no_disponible(monkeypatch) -> None:
    monkeypatch.setattr(ui_conftest, "detectar_error_qt", lambda: "qt-no-disponible")
    monkeypatch.delenv("HORAS_UI_SMOKE_CI", raising=False)

    with pytest.raises(pytest.skip.Exception, match="qt-no-disponible"):
        ui_conftest.require_qt()


def test_require_qt_falla_en_modo_estricto_si_qt_no_disponible(monkeypatch) -> None:
    monkeypatch.setattr(ui_conftest, "detectar_error_qt", lambda: "qt-no-disponible")
    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "1")

    with pytest.raises(RuntimeError, match="HORAS_UI_SMOKE_CI=1"):
        ui_conftest.require_qt()
