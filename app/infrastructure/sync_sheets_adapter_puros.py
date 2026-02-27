from __future__ import annotations

from collections.abc import Callable
from typing import Any


def build_service_operation(name: str, *args: Any) -> Callable[[Any], Any]:
    """Crea una operación invocable sobre SheetsSyncService sin tocar IO."""
    if not name or not isinstance(name, str):
        raise ValueError("El nombre de operación es obligatorio.")

    def _operation(service: Any) -> Any:
        method = getattr(service, name)
        return method(*args)

    return _operation


def normalize_sync_config_input(key: str, value: str) -> tuple[str, str]:
    clean_key = str(key).strip()
    if not clean_key:
        raise ValueError("La clave de configuración no puede estar vacía.")
    return clean_key, str(value).strip()


def normalize_pdf_log_input(persona_id: int, fechas: list[str], pdf_hash: str | None) -> tuple[int, list[str], str | None]:
    if persona_id <= 0:
        raise ValueError("persona_id debe ser mayor que cero.")
    # Comentario para junior: filtramos fechas vacías para evitar ruido en auditoría.
    clean_fechas = [str(fecha).strip() for fecha in fechas if str(fecha).strip()]
    clean_hash = str(pdf_hash).strip() if pdf_hash else None
    return persona_id, clean_fechas, clean_hash


def ensure_execution_plan_shape(plan: Any) -> Any:
    required = ("worksheet", "to_create", "to_update", "conflicts")
    if not all(hasattr(plan, attr) for attr in required):
        raise ValueError("El plan de sincronización no tiene el shape esperado.")
    return plan
