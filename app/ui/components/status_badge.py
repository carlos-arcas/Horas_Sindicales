from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    _TONES = {
        "success": "success",
        "warning": "warning",
        "error": "error",
        "neutral": "neutral",
    }

    def __init__(self, text: str = "", variant: str = "neutral", parent=None) -> None:
        super().__init__(text.upper(), parent)
        self.set_variant(variant)

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(text.upper())

    def set_variant(self, variant: str) -> None:
        self.setProperty("tone", self._TONES.get(variant, "neutral"))
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()
