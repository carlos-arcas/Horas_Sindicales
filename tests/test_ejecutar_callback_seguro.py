from __future__ import annotations

import logging

from app.ui.toasts.ejecutar_callback_seguro import ejecutar_callback_seguro


def test_ejecutar_callback_seguro_devuelve_true_si_no_hay_error(caplog) -> None:
    caplog.set_level(logging.ERROR)

    ok = ejecutar_callback_seguro(
        lambda: None,
        logger=logging.getLogger("tests.toast"),
        contexto="toast:test",
        correlation_id="CID-1",
    )

    assert ok is True
    assert not caplog.records


def test_ejecutar_callback_seguro_loguea_error_sin_ruta_sensible(caplog) -> None:
    caplog.set_level(logging.ERROR)

    def _callback() -> None:
        raise RuntimeError("fallo leyendo /home/user/secretos/credenciales.json")

    ok = ejecutar_callback_seguro(
        _callback,
        logger=logging.getLogger("tests.toast"),
        contexto="toast:test",
        correlation_id="CID-2",
    )

    assert ok is False
    assert len(caplog.records) == 1
    registro = caplog.records[0]
    assert registro.msg == "toast_action_callback_failed"
    assert registro.contexto == "toast:test"
    assert registro.correlation_id == "CID-2"
    assert registro.error_type == "RuntimeError"
    assert "/home/user/secretos/credenciales.json" not in registro.error_message
    assert "credenciales.json" in registro.error_message
