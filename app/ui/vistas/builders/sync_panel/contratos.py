from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QVBoxLayout, QWidget


@dataclass(frozen=True)
class TabSyncConstruida:
    tab: QWidget
    layout: QVBoxLayout
