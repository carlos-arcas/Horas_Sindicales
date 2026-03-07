from __future__ import annotations

import importlib
import os


def _humo_ui_estricto_activo() -> bool:
    return os.getenv("HORAS_UI_SMOKE_CI") == "1"


def detectar_error_qt() -> str | None:
    """Retorna mensaje de error si Qt no puede importarse de forma utilizable."""

    try:
        importlib.import_module("PySide6")
        importlib.import_module("PySide6.QtCore")
        importlib.import_module("PySide6.QtWidgets")
        return None
    except Exception as exc:  # pragma: no cover - depende del runner
        mensaje = f"PySide6/Qt no disponible para tests UI: {exc}"
        if "libGL.so.1" in str(exc):
            mensaje += (
                " (falta dependencia nativa 'libGL.so.1'; "
                "instalar paquete de sistema equivalente a libgl1)"
            )
        return mensaje
