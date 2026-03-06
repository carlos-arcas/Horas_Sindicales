"""Componentes de UI con importación tolerante a entornos sin backend gráfico.

Este paquete intenta exponer los widgets de forma perezosa/tolerante para evitar
fallos de importación en entornos *headless* (por ejemplo, CI sin PySide6 o con
problemas de librerías del sistema como libEGL).

En particular, ``CardWidget`` siempre se exporta: si su implementación real no
puede cargarse, se expone una clase de sustitución que falla de forma controlada
al instanciarse. Se recomienda importar/cargar widgets sólo donde se necesiten.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _safe_getattr(module_path: str, symbol: str) -> Any | None:
    try:
        module = import_module(module_path)
        return getattr(module, symbol)
    except Exception:
        return None


try:
    CardWidget = _safe_getattr("app.ui.components.card_widget", "CardWidget")
    if CardWidget is None:
        raise ImportError("CardWidget no disponible")
except Exception:

    class CardWidget:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "La funcionalidad de UI no está disponible en este entorno "
                "(PySide6/libEGL no disponible)."
            )


PrimaryButton = _safe_getattr("app.ui.components.primary_button", "PrimaryButton")
SaldosCard = _safe_getattr("app.ui.components.saldos_card", "SaldosCard")
SecondaryButton = _safe_getattr("app.ui.components.secondary_button", "SecondaryButton")
StatusBadge = _safe_getattr("app.ui.components.status_badge", "StatusBadge")
EmptyStateWidget = _safe_getattr("app.ui.components.empty_state", "EmptyStateWidget")

__all__ = [
    "SaldosCard",
    "CardWidget",
    "StatusBadge",
    "PrimaryButton",
    "SecondaryButton",
    "EmptyStateWidget",
]
