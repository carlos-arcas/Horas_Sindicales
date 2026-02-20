from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton

SPACING_BASE = 8
MODAL_BASE_WIDTH = 560


@dataclass(frozen=True)
class UiStatusPattern:
    label: str
    icon: str
    tone: str

    def as_badge(self) -> str:
        return f"{self.icon} {self.label}"


STATUS_PATTERNS: dict[str, UiStatusPattern] = {
    "CONFIRMED": UiStatusPattern("Confirmada", "✅", "success"),
    "PENDING": UiStatusPattern("Pendiente", "🕒", "pending"),
    "ERROR": UiStatusPattern("Error", "⛔", "error"),
    "WARNING": UiStatusPattern("Con avisos", "⚠", "warning"),
}


def status_badge(status: str) -> str:
    pattern = STATUS_PATTERNS.get(status)
    return pattern.as_badge() if pattern else status


def apply_modal_behavior(dialog: QDialog, *, primary_button: QPushButton | None = None) -> None:
    dialog.setMinimumWidth(MODAL_BASE_WIDTH)
    QShortcut(QKeySequence(Qt.Key_Escape), dialog, activated=dialog.reject)
    if primary_button is not None:
        primary_button.setDefault(True)
        primary_button.setAutoDefault(True)


def build_modal_actions(cancel_button: QPushButton, primary_button: QPushButton | None = None) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(SPACING_BASE)
    layout.addWidget(cancel_button)
    layout.addStretch(1)
    if primary_button is not None:
        layout.addWidget(primary_button)
    return layout
