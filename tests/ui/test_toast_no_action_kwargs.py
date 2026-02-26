from pathlib import Path
import re


SOURCE_PATH = Path("app/ui/vistas/main_window_vista.py")


def test_toast_success_error_do_not_pass_action_kwargs() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")

    success_calls = re.findall(r"self\.toast\.success\((?:.|\n)*?\)", source)
    error_calls = re.findall(r"self\.toast\.error\((?:.|\n)*?\)", source)

    assert success_calls, "No se encontraron llamadas a self.toast.success"
    assert error_calls, "No se encontraron llamadas a self.toast.error"

    for call in [*success_calls, *error_calls]:
        assert "action_label=" not in call
        assert "action_callback=" not in call


def test_safe_toast_wrappers_exist() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")

    assert "def _toast_success(" in source
    assert "def _toast_error(" in source
