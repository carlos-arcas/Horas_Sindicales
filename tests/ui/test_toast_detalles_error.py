from __future__ import annotations

import logging
import sys
from types import SimpleNamespace
from types import ModuleType
from typing import Any

import pytest

from app.ui.qt import slot_seguro
from app.ui.toasts.toast_actions import cerrar_toast


pytestmark = pytest.mark.headless_safe


class _SignalFalso:
    def __init__(self) -> None:
        self.payloads: list[str] = []

    def emit(self, value: str) -> None:
        self.payloads.append(value)


class _ToastFalso:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def error(self, message: str, **kwargs: Any) -> None:
        self.calls.append({"message": message, **kwargs})


def test_toast_cerrar_prioriza_senal_cuando_esta_disponible() -> None:
    signal = _SignalFalso()
    estado = {"closed": False}

    class _TarjetaFalsa:
        notificacion = SimpleNamespace(id="toast-1")
        cerrado = signal

        def close(self) -> None:
            estado["closed"] = True

    cerrar_toast(_TarjetaFalsa(), "toast-1")

    assert signal.payloads == ["toast-1"]
    assert estado["closed"] is False


def test_toast_cerrar_hace_close_si_no_hay_senal() -> None:
    estado = {"closed": False}

    class _TarjetaFalsaSinSignal:
        def close(self) -> None:
            estado["closed"] = True

    cerrar_toast(_TarjetaFalsaSinSignal(), "toast-2")

    assert estado["closed"] is True


def test_slot_seguro_error_publica_toast_con_callback_detalles() -> None:
    toast = _ToastFalso()

    def handler() -> None:
        raise RuntimeError("boom")

    slot = slot_seguro.envolver_slot_seguro(
        handler,
        contexto="builder:test",
        logger=logging.getLogger("test.slot.toast.detalles"),
        toast=toast,
    )

    slot()

    assert len(toast.calls) == 1
    call = toast.calls[0]
    assert callable(call.get("action_callback"))
    assert call.get("action_label")


def test_callback_detalles_usa_dialog_factory_inyectada() -> None:
    captured: list[dict[str, str | None]] = []

    callback = slot_seguro._crear_callback_detalles_error(
        titulo="titulo",
        resumen="resumen",
        detalle="detalle",
        incident_id="inc-1",
        logger=logging.getLogger("test.slot.dialogo"),
        dialog_factory=lambda **kwargs: captured.append(kwargs),
    )

    callback()

    assert captured == [
        {
            "titulo": "titulo",
            "resumen": "resumen",
            "detalle": "detalle",
            "incident_id": "inc-1",
        }
    ]


def test_dialogo_detalle_error_default_ejecuta_modal_y_no_depende_de_show() -> None:
    llamadas = {"exec": 0, "show": 0}

    class _DialogoFalso:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def exec(self) -> int:
            llamadas["exec"] += 1
            return 0

        def show(self) -> None:
            llamadas["show"] += 1

    modulo_falso = ModuleType("app.ui.dialogos.dialogo_detalle_error")
    modulo_falso.DialogoDetalleError = _DialogoFalso
    sys.modules[modulo_falso.__name__] = modulo_falso

    try:
        slot_seguro._abrir_dialogo_detalle_error_default(
            titulo="titulo",
            resumen="resumen",
            detalle="detalle",
            incident_id="inc-2",
        )
    finally:
        sys.modules.pop(modulo_falso.__name__, None)

    assert llamadas == {"exec": 1, "show": 0}
