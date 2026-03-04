from __future__ import annotations

from tests.helpers_main_window_ast import metodo_existe_en_mainwindow_o_mixins

REQUIRED_WIRING_HANDLERS = (
    "_on_completo_changed",
    "_on_add_pendiente",
    "_on_confirmar",
    "_update_solicitud_preview",
    "_apply_historico_default_range",
    "_status_to_label",
    "_normalize_input_heights",
    "_update_responsive_columns",
    "_configure_time_placeholders",
    "_configure_operativa_focus_order",
    "_configure_historico_focus_order",
)


def test_main_window_declara_handlers_minimos_de_wiring() -> None:
    missing = [name for name in REQUIRED_WIRING_HANDLERS if not metodo_existe_en_mainwindow_o_mixins(name)]
    assert not missing, (
        "MainWindow no cumple el contrato mínimo de handlers requerido por builders: "
        + ", ".join(missing)
    )
