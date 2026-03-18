from __future__ import annotations

import pytest

from app.application.modo_solo_lectura import crear_estado_modo_solo_lectura
from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    aplicar_politica_solo_lectura,
    resolver_control_mutante,
)
from tests.ui.harness_main_window import (
    build_app,
    build_window,
    close_window,
    pump_events,
)

qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QAction = qt_widgets.QAction
QWidget = qt_widgets.QWidget


def test_controles_mutantes_auditados_tienen_object_name_y_resuelven_ui_real(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_app()
    window = build_window(
        monkeypatch,
        estado_modo_solo_lectura=crear_estado_modo_solo_lectura(lambda: False),
    )

    try:
        pump_events()
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI:
            control = resolver_control_mutante(window, descriptor)
            assert control is not None, descriptor.nombre_control
            assert control.objectName() == descriptor.object_name, (
                descriptor.nombre_control
            )
            assert (
                getattr(window, descriptor.nombre_control).objectName()
                == descriptor.object_name
            )
            if descriptor.tipo_control == "action":
                assert isinstance(control, QAction)
            else:
                assert isinstance(control, QWidget)
    finally:
        close_window(window)
        app.processEvents()


def test_read_only_ui_real_deshabilita_mismos_controles_por_object_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_app()
    window = build_window(
        monkeypatch,
        estado_modo_solo_lectura=crear_estado_modo_solo_lectura(lambda: True),
    )

    try:
        pump_events()
        aplicar_politica_solo_lectura(window)
        pump_events()
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI:
            control = resolver_control_mutante(window, descriptor)
            assert control is not None, descriptor.nombre_control
            assert not control.isEnabled(), descriptor.nombre_control
    finally:
        close_window(window)
        app.processEvents()
