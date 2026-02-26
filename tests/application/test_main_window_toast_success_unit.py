from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace


class _LoggerSpy:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message)


class _FakeToastNoKwargs:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def success(self, message: str, title: str | None = None) -> None:
        self.calls.append((message, title))


def _load_toast_success_method():
    source_path = Path("app/ui/vistas/main_window_vista.py")
    module = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    class_node = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    method_node = next(
        node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == "_toast_success"
    )

    isolated_module = ast.Module(body=[method_node], type_ignores=[])
    ast.fix_missing_locations(isolated_module)

    logger_spy = _LoggerSpy()
    namespace: dict[str, object] = {"logger": logger_spy}
    exec(compile(isolated_module, filename=str(source_path), mode="exec"), namespace)
    return namespace["_toast_success"], logger_spy


def test_toast_success_reintenta_sin_kwargs_si_toast_no_los_soporta() -> None:
    method, logger_spy = _load_toast_success_method()
    fake_toast = _FakeToastNoKwargs()
    instance = SimpleNamespace(toast=fake_toast)

    method(instance, "PDF generado correctamente", title="Confirmación", action_label="Abrir PDF")

    assert fake_toast.calls == [
        ("PDF generado correctamente", "Confirmación"),
    ]
    assert any("UI_TOAST_DEGRADED" in message for message in logger_spy.messages)
