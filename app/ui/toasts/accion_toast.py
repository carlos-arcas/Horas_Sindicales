from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class AccionToast:
    etiqueta: str | None = None
    callback: Callable[[], None] | None = None

    @classmethod
    def desde_argumentos(
        cls,
        *,
        action_label: str | None,
        action_callback: Callable[[], None] | None,
        action_text: object | None = None,
        action: object | None = None,
    ) -> AccionToast:
        etiqueta = action_label if isinstance(action_label, str) else None
        if etiqueta is None and isinstance(action_text, str):
            etiqueta = action_text

        callback = action_callback if callable(action_callback) else None
        if callback is None and callable(action):
            callback = action

        return cls(etiqueta=etiqueta, callback=callback)
