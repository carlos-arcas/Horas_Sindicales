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
