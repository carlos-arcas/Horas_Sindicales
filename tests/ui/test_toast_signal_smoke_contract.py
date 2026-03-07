from __future__ import annotations

from pathlib import Path


def test_toast_action_signal_slot_exists() -> None:
    source = Path("app/ui/widgets/widget_toast.py").read_text(encoding="utf-8")
    assert "self._btn_accion.clicked.connect(self._ejecutar_accion)" in source
    assert "def _ejecutar_accion" in source
