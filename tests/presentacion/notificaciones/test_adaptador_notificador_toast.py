from __future__ import annotations

import threading

from aplicacion.notificaciones.dto_toast import NivelToast, NotificacionToastDTO
from presentacion.notificaciones.adaptador_notificador_toast import ToastControllerAdapter


def _crear_toast() -> NotificacionToastDTO:
    return NotificacionToastDTO(
        nivel=NivelToast.SUCCESS,
        titulo="Guardado",
        mensaje="Cambios guardados",
        duracion_ms=1500,
    )


def test_notificar_emite_signal_con_dto(qtbot) -> None:
    adapter = ToastControllerAdapter()
    toast = _crear_toast()

    with qtbot.waitSignal(adapter.toast_emitido, timeout=1000) as blocker:
        adapter.notificar(toast)

    assert blocker.args == [toast]


def test_notificar_desde_hilo_secundario_emite_signal(qtbot) -> None:
    adapter = ToastControllerAdapter()
    toast = _crear_toast()

    def _worker() -> None:
        adapter.notificar(toast)

    worker = threading.Thread(target=_worker)

    with qtbot.waitSignal(adapter.toast_emitido, timeout=2000) as blocker:
        worker.start()
        worker.join(timeout=1)

    assert not worker.is_alive()
    assert blocker.args == [toast]
