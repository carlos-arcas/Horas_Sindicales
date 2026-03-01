from __future__ import annotations


def conectar_signal(window, signal, handler_name: str, *, contexto: str) -> None:
    handler = getattr(window, handler_name, None)
    if not callable(handler):
        raise RuntimeError(f"Falta handler {handler_name} requerido por {contexto}")
    signal.connect(handler)
