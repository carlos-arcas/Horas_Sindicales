from pathlib import Path


SOURCE_PATH = Path("app/ui/vistas/main_window_vista.py")


def test_toast_success_error_do_not_pass_action_kwargs() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")

    forbidden_kw_a = "action_label" + "="
    forbidden_kw_b = "action_callback" + "="
    assert forbidden_kw_a not in source
    assert forbidden_kw_b not in source


def test_safe_toast_wrappers_exist() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")

    assert "def _toast_success(" in source
    assert "def _toast_error(" in source


def test_toast_manager_supports_action_kwargs_in_success_error() -> None:
    source = Path("app/ui/widgets/toast.py").read_text(encoding="utf-8")

    assert "def success(" in source
    assert "action_label: str | None = None" in source
    assert "action_callback: Callable[[], None] | None = None" in source
    assert "def error(" in source
    assert "details: str | None = None" in source
