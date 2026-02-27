from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import logging
import pytest
from tests.ui.conftest import require_qt

require_qt()

from app.ui.vistas.main_window_vista import MainWindow




def test_confirmar_handler_exists_in_main_window() -> None:
    assert hasattr(MainWindow, "_on_confirmar")

def test_on_confirmar_muestra_aviso_si_no_hay_seleccion(caplog: pytest.LogCaptureFixture) -> None:
    """Garantiza que no hay retorno silencioso al confirmar sin filas seleccionadas."""

    caplog.set_level(logging.INFO)
    toast_warning = Mock()
    fake_window = SimpleNamespace(
        _ui_ready=True,
        _run_preconfirm_checks=lambda: True,
        _current_persona=lambda: SimpleNamespace(id=1),
        _selected_pending_for_editing=lambda: None,
        _selected_pending_solicitudes=lambda: [],
        _selected_pending_row_indexes=lambda: [],
        _pending_conflict_rows=set(),
        _dump_estado_pendientes=lambda motivo: {"motivo": motivo},
        _prompt_confirm_pdf_path=lambda selected: (_ for _ in ()).throw(AssertionError("No debe pedir ruta PDF sin selección")),
        _execute_confirmar_with_pdf=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe ejecutar confirmación sin selección")),
        _finalize_confirmar_with_pdf=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe finalizar confirmación sin selección")),
        fecha_input=SimpleNamespace(date=lambda: SimpleNamespace(toString=lambda _fmt: "2026-01-01")),
        desde_input=SimpleNamespace(time=lambda: SimpleNamespace(toString=lambda _fmt: "09:00")),
        hasta_input=SimpleNamespace(time=lambda: SimpleNamespace(toString=lambda _fmt: "17:00")),
        toast=SimpleNamespace(warning=toast_warning),
    )

    MainWindow._on_confirmar(fake_window)

    toast_warning.assert_called_once()
    assert "UI_CLICK_CONFIRMAR_PDF" in caplog.text
    assert "UI_CONFIRMAR_PDF_RETURN_EARLY" in caplog.text
