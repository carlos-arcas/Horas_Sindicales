from __future__ import annotations

import pytest

try:
    from app.ui.vistas.main_window import dialogos_sincronizacion
    from app.ui.vistas.main_window.state_controller import MainWindow
except ImportError as exc:  # pragma: no cover - depende del entorno de Qt
    pytest.skip(f"Qt no disponible para este test: {exc}", allow_module_level=True)


def test_status_to_label_reusa_mapping_canonico_para_idle() -> None:
    label = MainWindow._status_to_label(object(), "IDLE")

    assert label == dialogos_sincronizacion.status_to_label("IDLE")
    assert label.strip()


def test_status_to_label_fallback_en_estado_desconocido() -> None:
    assert MainWindow._status_to_label(object(), "UNKNOWN_STATUS") == "UNKNOWN_STATUS"
