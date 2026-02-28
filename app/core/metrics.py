from __future__ import annotations

from functools import wraps
from threading import Lock
from time import perf_counter
from typing import Any, Callable


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._timings: dict[str, list[float]] = {}

    def contador(self, nombre: str) -> int:
        with self._lock:
            return self._counters.get(nombre, 0)

    def incrementar(self, nombre: str, valor: int = 1) -> None:
        with self._lock:
            self._counters[nombre] = self._counters.get(nombre, 0) + valor

    def registrar_tiempo(self, nombre: str, milisegundos: float) -> None:
        with self._lock:
            bucket = self._timings.setdefault(nombre, [])
            bucket.append(milisegundos)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            counters = dict(self._counters)
            timings = {name: list(values) for name, values in self._timings.items()}
        return {
            "counters": counters,
            "timings_ms": {
                name: {
                    "count": len(values),
                    "last": values[-1] if values else 0.0,
                    "avg": (sum(values) / len(values)) if values else 0.0,
                    "max": max(values) if values else 0.0,
                }
                for name, values in timings.items()
            },
        }


metrics_registry = MetricsRegistry()


def medir_tiempo(nombre_metrica: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            inicio = perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (perf_counter() - inicio) * 1000
                metrics_registry.registrar_tiempo(nombre_metrica, elapsed_ms)

        return wrapper

    return decorator
