from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSpinBox, QWidget

from app.domain.time_utils import hm_to_minutes, minutes_to_hm


class MinuteSpinBox(QSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRange(0, 59)

    def textFromValue(self, value: int) -> str:
        return f"{value:02d}"

    def valueFromText(self, text: str) -> int:
        return int(text.strip() or 0)


class TimeEditHM(QWidget):
    minutesChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._hours_spin = QSpinBox()
        self._hours_spin.setRange(0, 9999)
        self._hours_spin.setSuffix(" h")
        self._hours_spin.setFixedWidth(70)
        layout.addWidget(self._hours_spin)

        self._minutes_spin = MinuteSpinBox()
        self._minutes_spin.setSuffix(" m")
        self._minutes_spin.setFixedWidth(60)
        layout.addWidget(self._minutes_spin)

        layout.addStretch(1)

        self._hours_spin.valueChanged.connect(self._emit_minutes_changed)
        self._minutes_spin.valueChanged.connect(self._emit_minutes_changed)

    def _emit_minutes_changed(self) -> None:
        self.minutesChanged.emit(self.minutes())

    def set_minutes(self, minutes: int) -> None:
        horas, mins = minutes_to_hm(minutes)
        self._hours_spin.setValue(horas)
        self._minutes_spin.setValue(mins)

    def minutes(self) -> int:
        return hm_to_minutes(self._hours_spin.value(), self._minutes_spin.value())

    def set_hour_range(self, minimum: int, maximum: int) -> None:
        self._hours_spin.setRange(minimum, maximum)

