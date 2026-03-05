from __future__ import annotations


def calcular_elapsed_ms(inicio_monotonic: float, ahora_monotonic: float) -> int:
    """Calcula milisegundos transcurridos usando reloj monotónico."""
    delta = max(0.0, ahora_monotonic - inicio_monotonic)
    return int(delta * 1000)


def debe_disparar_timeout(
    *,
    boot_finalizado: bool,
    timeout_ms: int,
    elapsed_ms: int,
) -> bool:
    if boot_finalizado:
        return False
    if timeout_ms <= 0:
        return True
    return elapsed_ms >= timeout_ms
