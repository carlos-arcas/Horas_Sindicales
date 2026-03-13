from __future__ import annotations

from pathlib import Path


def test_toast_action_signal_slot_exists() -> None:
    source = Path("app/ui/widgets/widget_toast.py").read_text(encoding="utf-8")
    assert "self._btn_accion.clicked.connect(self._ejecutar_accion)" in source
    assert "def _ejecutar_accion" in source



def test_toast_detalles_slot_nombrado_y_sin_lambda() -> None:
    source = Path("app/ui/widgets/widget_toast.py").read_text(encoding="utf-8")
    assert "def _emitir_solicitud_detalles" in source
    assert "clicked.connect(self._emitir_solicitud_detalles)" in source
    assert "clicked.connect(lambda" not in source


def test_overlay_ignora_mouse_fuera_de_toast() -> None:
    source = Path("app/ui/widgets/overlay_toast.py").read_text(encoding="utf-8")
    assert "def _debe_ignorar_evento_mouse" in source
    assert "self.childAt(posicion) is None" in source
