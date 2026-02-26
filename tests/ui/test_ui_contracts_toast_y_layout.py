from __future__ import annotations

from pathlib import Path


def _source() -> str:
    return Path("app/ui/vistas/main_window_vista.py").read_text(encoding="utf-8")


def test_toast_error_tiene_accion_ver_detalle_con_handler() -> None:
    source = _source()
    assert 'action_label="Ver detalle"' in source
    assert "def _show_error_detail(" in source


def test_labels_clave_sin_fondo_gris_en_stylesheet_inline() -> None:
    source = _source().lower()
    assert "setstylesheet(\"background" not in source
    assert "#eee" not in source


def test_notas_en_datos_reserva_y_no_en_seccion_independiente() -> None:
    source = _source()
    assert 'QLabel("Datos de la Reserva")' in source
    assert 'QLabel("Observaciones")' not in source


def test_pendientes_siempre_desplegados_sin_disclosure() -> None:
    source = _source()
    assert "self.pending_details_button.setCheckable(False)" in source
    assert "self.pending_details_content.setVisible(True)" in source
