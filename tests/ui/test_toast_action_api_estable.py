from __future__ import annotations

from pathlib import Path

from app.ui.toasts.accion_toast import AccionToast


def test_accion_toast_resuelve_aliases_y_callback() -> None:
    accion = AccionToast.desde_argumentos(
        action_label=None,
        action_callback=None,
        action_text="Detalle",
        action=lambda: None,
    )

    assert accion.etiqueta == "Detalle"
    assert callable(accion.callback)


def test_toast_manager_api_incluye_kwargs_de_accion_en_success_y_error() -> None:
    source = Path("app/ui/widgets/toast.py").read_text(encoding="utf-8")

    assert "def success(" in source
    assert "action_label: str | None = None" in source
    assert "action_callback: Callable[[], None] | None = None" in source
    assert "def error(" in source
    assert "action_label=accion.etiqueta" in source
    assert "action_callback=accion.callback" in source
