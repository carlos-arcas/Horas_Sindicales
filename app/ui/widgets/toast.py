from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import logging

from PySide6.QtCore import QEvent, QObject, QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

LEVELS = {"info", "success", "warning", "error"}
POSITIONS = {"top-right", "top-left", "bottom-right", "bottom-left"}

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

TOAST_LEVEL_ACCENTS = {
    "success": "#3FAF6A",
    "info": "#4C93F0",
    "warning": "#D09A34",
    "error": "#D35E5E",
}


@dataclass(slots=True)
class ToastRequest:
    message: str
    level: str = "info"
    title: str | None = None
    duration_ms: int = 3000
    close_on_click: bool = True
    action_label: str | None = None
    action_callback: Callable[[], None] | None = None


class ToastWidget(QFrame):
    closed = Signal(object)

    def __init__(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
        close_on_click: bool = True,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.level = level if level in LEVELS else "info"
        self._duration_ms = (
            DEFAULT_DURATIONS_MS[self.level] if duration_ms is None else max(0, int(duration_ms))
        )
        self._remaining_ms = self._duration_ms
        self._is_closing = False
        self._close_on_click = close_on_click

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("toastWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        self._action_callback = action_callback
        self._build_ui(message, title, action_label)
        self._apply_style()

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.close_animated)

        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.finished.connect(self._finalize_close)

        if self._duration_ms > 0:
            self._start_timer(self._duration_ms)

    def _build_ui(self, message: str, title: str | None, action_label: str | None) -> None:
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

        if action_label and self._action_callback is not None:
            action_button = QPushButton(action_label)
            action_button.setObjectName("toastActionButton")
            action_button.clicked.connect(self._on_action_clicked)
            root.addWidget(action_button, 0, Qt.AlignmentFlag.AlignTop)

        close_button = QPushButton("×")
        close_button.setObjectName("toastCloseButton")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close_animated)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)

        self.setMinimumWidth(300)
        self.setMaximumWidth(420)

    def _apply_style(self) -> None:
        palette = QApplication.palette()
        base = palette.window().color().name()
        text = palette.windowText().color().name()
        accent = TOAST_LEVEL_ACCENTS.get(self.level, TOAST_LEVEL_ACCENTS["info"])
        hover = QColor(text).lighter(130).name()
        self.setStyleSheet(
            f"""
            QWidget#toastWidget {{
                background-color: {base};
                border: 1px solid {accent};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
            QLabel[role="toastIcon"] {{
                font-size: 16px;
                font-weight: 700;
                color: {accent};
                min-width: 16px;
            }}
            QLabel[role="toastTitle"] {{
                font-weight: 700;
                color: {text};
            }}
            QLabel[role="toastMessage"] {{
                color: {text};
            }}
            QPushButton#toastCloseButton {{
                border: none;
                background: transparent;
                color: {text};
                font-size: 16px;
                font-weight: 700;
                padding: 0px 4px;
            }}
            QPushButton#toastCloseButton:hover {{
                color: {hover};
            }}
            QPushButton#toastActionButton {{
                background-color: transparent;
                border: 1px solid {accent};
                border-radius: 6px;
                padding: 2px 8px;
                color: {text};
                font-weight: 600;
            }}
            """
        )

    def _on_action_clicked(self) -> None:
        if self._action_callback is not None:
            self._action_callback()
        self.close_animated()

    def _start_timer(self, timeout_ms: int) -> None:
        self._remaining_ms = max(0, timeout_ms)
        self._auto_hide_timer.start(self._remaining_ms)

    def play_show_animation(self) -> None:
        self._fade_in.stop()
        self._fade_in.start()

    def close_animated(self) -> None:
        if self._is_closing:
            return
        self._is_closing = True
        self._auto_hide_timer.stop()
        self._fade_out.stop()
        self._fade_out.setStartValue(self._opacity.opacity())
        self._fade_out.setEndValue(0.0)
        self._fade_out.start()

    def _finalize_close(self) -> None:
        self.closed.emit(self)
        self.hide()
        self.deleteLater()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        super().enterEvent(event)
        if not self._auto_hide_timer.isActive():
            return
        self._remaining_ms = self._auto_hide_timer.remainingTime()
        self._auto_hide_timer.stop()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        super().leaveEvent(event)
        if self._duration_ms <= 0 or self._remaining_ms <= 0 or self._is_closing:
            return
        self._auto_hide_timer.start(self._remaining_ms)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._close_on_click and event.button() == Qt.MouseButton.LeftButton:
            self.close_animated()
        super().mousePressEvent(event)

    def force_dispose(self) -> None:
        self._auto_hide_timer.stop()
        self._fade_in.stop()
        self._fade_out.stop()
        self._is_closing = True
        self.hide()
        self.deleteLater()


Toast = ToastWidget


class ToastManager(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        max_on_screen: int = 3,
        position: str = "top-right",
        spacing: int = 10,
    ) -> None:
        super().__init__(parent)
        self._host: QWidget | None = None
        self._active_toasts: list[ToastWidget] = []
        self._queue: deque[ToastRequest] = deque()
        self._max_on_screen = max(1, int(max_on_screen))
        self._position = position if position in POSITIONS else "top-right"
        self._spacing = max(0, int(spacing))
        self._is_active = False
        self._margin = 12
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

    def show(
        self,
        message: str | None = None,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = 3000,
        **opts: object,
    ) -> None:
        if message is None:
            super().show()
            return
        normalized_level = level if level in LEVELS else "info"
        duration_value = DEFAULT_DURATIONS_MS[normalized_level] if duration_ms is None else int(duration_ms)
        payload = {
            "message": message,
            "level": normalized_level,
            "title": title,
            "duration_ms": duration_value,
            "close_on_click": bool(opts.get("close_on_click", True)),
            "action_label": opts.get("action_label") if isinstance(opts.get("action_label"), str) else None,
            "action_callback": opts.get("action_callback") if callable(opts.get("action_callback")) else None,
        }
        req = ToastRequest(**payload)
        self._enqueue_or_spawn(req)

    def show_info(
        self, message: str, title: str | None = None, duration_ms: int | None = 3000, **opts: object
    ) -> None:
        self.show(message=message, level="info", title=title, duration_ms=duration_ms, **opts)

    def show_success(
        self, message: str, title: str | None = None, duration_ms: int | None = 3000, **opts: object
    ) -> None:
        self.show(message=message, level="success", title=title, duration_ms=duration_ms, **opts)

    def show_warning(
        self, message: str, title: str | None = None, duration_ms: int | None = 3000, **opts: object
    ) -> None:
        self.show(message=message, level="warning", title=title, duration_ms=duration_ms, **opts)

    def show_error(
        self, message: str, title: str | None = None, duration_ms: int | None = 3000, **opts: object
    ) -> None:
        self.show(message=message, level="error", title=title, duration_ms=duration_ms, **opts)

    # Compat API
    def show_toast(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.show(message=message, level=level, title=title, duration_ms=duration_ms)

    def add_toast(
        self,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.show_toast(message=message, level=level, title=title, duration_ms=duration_ms)

    def success(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_success(message=message, title=title, duration_ms=3000 if duration_ms is None else duration_ms)

    def info(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_info(message=message, title=title, duration_ms=3000 if duration_ms is None else duration_ms)

    def warning(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_warning(message=message, title=title, duration_ms=3000 if duration_ms is None else duration_ms)

    def error(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_error(message=message, title=title, duration_ms=3000 if duration_ms is None else duration_ms)

    def _enqueue_or_spawn(self, request: ToastRequest) -> None:
        if not self._is_active:
            logger.warning("ToastManager no activo. Toast descartado: %s", request.message)
            return
        if self._get_host() is None:
            logger.warning("ToastManager sin host válido. Toast descartado: %s", request.message)
            return
        if len(self._active_toasts) < self._max_on_screen:
            self._spawn_toast(request)
            return
        self._queue.append(request)

    def _spawn_toast(self, request: ToastRequest) -> None:
        toast_payload = {
            "message": request.message,
            "level": request.level,
            "title": request.title,
            "duration_ms": request.duration_ms,
            "close_on_click": request.close_on_click,
            "action_label": request.action_label,
            "action_callback": request.action_callback,
            "parent": self,
        }
        toast = ToastWidget(**toast_payload)
        toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        toast.closed.connect(self._on_toast_finished)
        self._active_toasts.append(toast)
        toast.show()
        toast.play_show_animation()
        self._reposition()

    def _on_toast_finished(self, toast: object) -> None:
        if isinstance(toast, ToastWidget):
            self._active_toasts = [item for item in self._active_toasts if item is not toast]
        if self._queue and self._get_host() is not None and self._is_active:
            self._spawn_toast(self._queue.popleft())
        self._reposition()

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
        self._deactivate_manager()

    def _deactivate_manager(self) -> None:
        self._clear_toasts()
        self._queue.clear()
        self._host = None
        self._is_active = False
        self.hide()

    def _on_host_destroyed(self, *_args: object) -> None:
        self._deactivate_manager()

    def _clear_toasts(self) -> None:
        for toast in self._active_toasts:
            try:
                toast.closed.disconnect(self._on_toast_finished)
            except (RuntimeError, TypeError):
                pass
            try:
                toast.force_dispose()
            except RuntimeError:
                pass
        self._active_toasts = []

    def _reposition(self) -> None:
        host = self._get_host()
        if host is None:
            return
        self.setGeometry(host.rect())

        valid_toasts = [toast for toast in self._active_toasts if toast.isVisible()]
        self._active_toasts = valid_toasts

        is_top = self._position.startswith("top")
        is_right = self._position.endswith("right")

        current_y = self._margin if is_top else self.height() - self._margin
        toasts = valid_toasts if is_top else list(reversed(valid_toasts))

        for toast in toasts:
            hint = toast.sizeHint()
            x = self.width() - hint.width() - self._margin if is_right else self._margin
            y = current_y if is_top else current_y - hint.height()
            toast.move(QPoint(max(self._margin, x), max(self._margin, y)))
            current_y = (
                current_y + hint.height() + self._spacing
                if is_top
                else current_y - hint.height() - self._spacing
            )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        host = self._get_host()
        if host is not None and watched is host and event.type() in (QEvent.Resize, QEvent.Move):
            self._reposition()
        return super().eventFilter(watched, event)
