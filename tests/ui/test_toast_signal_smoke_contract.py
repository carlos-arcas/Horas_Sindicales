from __future__ import annotations

from pathlib import Path


def test_toast_action_signal_slot_exists() -> None:
    source = Path("app/ui/widgets/toast.py").read_text(encoding="utf-8")
    assert "action_button.clicked.connect(self._on_action_clicked)" in source
    assert "def _on_action_clicked" in source
