from __future__ import annotations

import logging

from app.ui.toasts.ejecutar_callback_seguro import ejecutar_callback_seguro


def test_ejecutar_callback_seguro_captura_excepcion_y_no_propaga(caplog) -> None:
    def callback_fallido() -> None:
        raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR):
        ejecutado = ejecutar_callback_seguro(
            callback_fallido,
            logger=logging.getLogger("tests.toast"),
            contexto="/tmp/super/secreto/callback.py",
            correlation_id="cid-123",
        )

    assert ejecutado is False
    assert "toast_action_callback_failed" in caplog.text
    registro = caplog.records[-1]
    assert getattr(registro, "correlation_id", None) == "cid-123"
    assert getattr(registro, "contexto", None) == ".../secreto/callback.py"


def test_ejecutar_callback_seguro_retorna_true_si_ejecuta_callback() -> None:
    estado = {"valor": 0}

    def callback_ok() -> None:
        estado["valor"] = 1

    ejecutado = ejecutar_callback_seguro(
        callback_ok,
        logger=logging.getLogger("tests.toast"),
        contexto="toast:success:abrir",
        correlation_id=None,
    )

    assert ejecutado is True
    assert estado["valor"] == 1


def test_tarjeta_toast_usa_helper_seguro_para_acciones() -> None:
    source = open("app/ui/widgets/widget_toast.py", encoding="utf-8").read()

    assert "ejecutar_callback_seguro(" in source
    assert "toast_action_callback_failed" not in source
