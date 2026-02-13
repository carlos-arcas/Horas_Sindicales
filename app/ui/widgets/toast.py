from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ToastPalette:
    bg: str
    border: str
    text: str


TOAST_STYLES: dict[str, ToastPalette] = {
    "success": ToastPalette("#6FCF97", "#2F8F55", "#000000"),
    "info": ToastPalette("#5BA6F6", "#1D5FA8", "#000000"),
    "warning": ToastPalette("#F2B441", "#A06912", "#000000"),
    "error": ToastPalette("#EB6B6B", "#A32D2D", "#000000"),
}

TOAST_ICONS = {
    "success": "✓",
    "info": "ℹ",
    "warning": "⚠",
    "error": "⛔",
}

DEFAULT_DURATIONS_MS = {
    "success": 3000,
    "info": 3000,
    "warning": 5000,
    "error": 8000,
}


class ToastWidget(QFrame):
    def __init__(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.level = level if level in TOAST_STYLES else "info"
        self._duration_ms = (
            DEFAULT_DURATIONS_MS[self.level] if duration_ms is None else max(0, int(duration_ms))
        )
        self._remaining_ms = self._duration_ms
        self._started_at_ms = 0

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("toastWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(1.0)

        self._build_ui(message, title)
        self._apply_style()

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.close_animated)

        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(220)
        self._fade.finished.connect(self.deleteLater)

        if self._duration_ms > 0:
            self._start_timer(self._duration_ms)

    def _build_ui(self, message: str, title: str | None) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 8, 8)
        root.setSpacing(10)

        icon = QLabel(TOAST_ICONS.get(self.level, "ℹ"))
        icon.setProperty("role", "toastIcon")
        root.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        if title:
            title_label = QLabel(title)
            title_label.setProperty("role", "toastTitle")
            text_col.addWidget(title_label)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setProperty("role", "toastMessage")
        text_col.addWidget(message_label)
        root.addLayout(text_col, 1)

        close_button = QPushButton("×")
        close_button.setObjectName("toastCloseButton")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close_animated)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)

        self.setMinimumWidth(300)
        self.setMaximumWidth(420)

    def _apply_style(self) -> None:
        palette = TOAST_STYLES[self.level]
        self.setStyleSheet(
            f"""
            QWidget#toastWidget {{
                background-color: {palette.bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QLabel[role="toastIcon"] {{
                font-size: 16px;
                font-weight: 700;
                color: #000;
                min-width: 16px;
            }}
            QLabel[role="toastTitle"] {{
                font-weight: 700;
                color: #000;
            }}
            QLabel[role="toastMessage"] {{
                color: #000;
            }}
            QPushButton#toastCloseButton {{
                border: none;
                background: transparent;
                color: #000;
                font-size: 16px;
                font-weight: 700;
                padding: 0px 4px;
            }}
            QPushButton#toastCloseButton:hover {{
                color: {QColor("#000000").lighter(140).name()};
            }}
            """
        )

    def _start_timer(self, timeout_ms: int) -> None:
        self._remaining_ms = max(0, timeout_ms)
        self._started_at_ms = 0
        self._auto_hide_timer.start(self._remaining_ms)

    def close_animated(self) -> None:
        if self._fade.state() == QPropertyAnimation.Running:
            return
        self._auto_hide_timer.stop()
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        super().enterEvent(event)
        if not self._auto_hide_timer.isActive():
            return
        self._remaining_ms = self._auto_hide_timer.remainingTime()
        self._auto_hide_timer.stop()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        super().leaveEvent(event)
        if self._duration_ms <= 0 or self._remaining_ms <= 0:
            return
        self._auto_hide_timer.start(self._remaining_ms)

    def force_dispose(self) -> None:
        self._auto_hide_timer.stop()
        self._fade.stop()
        self.hide()
        self.deleteLater()


class ToastManager(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._host: QWidget | None = None
        self._toasts: list[ToastWidget] = []
        self._is_active = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def attach_to(self, main_window: QWidget) -> None:
        self._detach_host()
        self.setParent(main_window)
        self._host = main_window
        self._is_active = True
        self.setGeometry(main_window.rect())
        self.show()
        main_window.installEventFilter(self)
        main_window.destroyed.connect(self._on_host_destroyed, Qt.ConnectionType.QueuedConnection)

    def show_toast(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        if not self._is_active:
            return
        if not self._get_host():
            return
        toast = ToastWidget(message=message, level=level, title=title, duration_ms=duration_ms, parent=self)
        toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        toast.destroyed.connect(self._on_toast_destroyed)
        self._toasts.append(toast)
        toast.show()
        self._reposition()

    def success(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_toast(message, level="success", title=title, duration_ms=duration_ms)

    def info(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_toast(message, level="info", title=title, duration_ms=duration_ms)

    def warning(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_toast(message, level="warning", title=title, duration_ms=duration_ms)

    def error(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_toast(message, level="error", title=title, duration_ms=duration_ms)

    def _get_host(self) -> QWidget | None:
        if not self._is_active or self._host is None:
            return None
        try:
            _ = self._host.objectName()
        except RuntimeError:
            return None
        return self._host

    def _detach_host(self) -> None:
        host = self._get_host()
        if host is not None:
            host.removeEventFilter(self)
            try:
                host.destroyed.disconnect(self._on_host_destroyed)
            except (RuntimeError, TypeError):
                pass
        self._clear_toasts()
        self._host = None
        self._is_active = False

    def _on_host_destroyed(self, *_args: object) -> None:
        self._clear_toasts()
        self._host = None
        self._is_active = False
        self.hide()

    def _clear_toasts(self) -> None:
        for toast in self._toasts:
            try:
                toast.destroyed.disconnect(self._on_toast_destroyed)
            except (RuntimeError, TypeError):
                pass
            try:
                toast.force_dispose()
            except RuntimeError:
                pass
        self._toasts = []

    def _on_toast_destroyed(self, *_args: object) -> None:
        sender = self.sender()
        if isinstance(sender, ToastWidget):
            self._remove_toast(sender)

    def _remove_toast(self, toast: ToastWidget) -> None:
        self._toasts = [item for item in self._toasts if item is not toast and item.isVisible()]
        if self._get_host() is None:
            return
        self._reposition()

    def _reposition(self) -> None:
        host = self._get_host()
        if host is None:
            return
        self.setGeometry(host.rect())
        margin = 12
        spacing = 10
        y = margin
        for toast in self._toasts:
            if not toast.isVisible():
                continue
            hint = toast.sizeHint()
            x = max(margin, (self.width() - hint.width()) // 2)
            toast.move(QPoint(x, y))
            y += hint.height() + spacing

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        host = self._get_host()
        if host is not None and watched is host and event.type() in (QEvent.Resize, QEvent.Move):
            self._reposition()
        return super().eventFilter(watched, event)
