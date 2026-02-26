from __future__ import annotations

from app.ui.toast_compat import ui_toast_error, ui_toast_success


class FakeToastNoAction:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def success(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.calls.append((message, title))

    def error(self, message: str, title: str | None = None, duration_ms: int | None = None) -> None:
        self.calls.append((message, title))


class FakeToastWithAction:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def success(self, message: str, title: str | None = None, **opts: object) -> None:
        self.kwargs = {"message": message, "title": title, **opts}

    def error(self, message: str, title: str | None = None, **opts: object) -> None:
        self.kwargs = {"message": message, "title": title, **opts}


def test_ui_toast_success_fallback_when_actions_are_not_supported() -> None:
    toast = FakeToastNoAction()

    used_native_action = ui_toast_success(
        toast,
        "ok",
        title="T",
        action_text="Abrir",
        action=lambda: None,
    )

    assert used_native_action is False
    assert toast.calls == [("ok", "T")]


def test_ui_toast_error_passes_action_kwargs_when_supported() -> None:
    toast = FakeToastWithAction()

    used_native_action = ui_toast_error(
        toast,
        "boom",
        title="Error",
        action_text="Detalle",
        action=lambda: None,
    )

    assert used_native_action is True
    assert toast.kwargs is not None
    assert toast.kwargs["action_label"] == "Detalle"
    assert callable(toast.kwargs["action_callback"])
