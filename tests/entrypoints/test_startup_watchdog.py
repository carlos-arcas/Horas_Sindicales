from __future__ import annotations

from app.entrypoints.startup_watchdog import calcular_elapsed_ms, debe_disparar_timeout


def test_debe_disparar_timeout_según_elapsed() -> None:
    assert debe_disparar_timeout(boot_finalizado=False, timeout_ms=1000, elapsed_ms=999) is False
    assert debe_disparar_timeout(boot_finalizado=False, timeout_ms=1000, elapsed_ms=1000) is True


def test_debe_disparar_timeout_respeta_boot_finalizado() -> None:
    assert debe_disparar_timeout(boot_finalizado=True, timeout_ms=1, elapsed_ms=99999) is False


def test_calcular_elapsed_ms_trunca_y_no_devuelve_negativo() -> None:
    assert calcular_elapsed_ms(10.0, 10.2509) == 250
    assert calcular_elapsed_ms(10.0, 9.0) == 0
