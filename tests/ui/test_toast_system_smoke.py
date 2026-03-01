from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

require_qt()

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QMainWindow

from app.ui.widgets.toast import GestorToasts
from app.ui.widgets.toast import NotificacionToast


class _FakeAdapter(QObject):
    toast_requested = Signal(object)


def _dto(idx: int, *, duracion_ms: int = 8000, detalles: str | None = None, correlacion_id: str | None = None) -> NotificacionToast:
    return NotificacionToast(
        id=f"toast-{idx}",
        titulo=f"Título {idx}",
        mensaje=f"Mensaje {idx}",
        nivel="info",
        detalles=detalles,
        correlacion_id=correlacion_id,
        duracion_ms=duracion_ms,
    )


def test_emitir_senal_adapter_muestra_toast(qtbot) -> None:
    window = QMainWindow()
    window.resize(900, 700)
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    adapter = _FakeAdapter()
    assert manager.conectar_adaptador(adapter)

    adapter.toast_requested.emit(_dto(1))
    qtbot.wait(50)

    assert len(manager._visibles) == 1


def test_stack_maximo_tres_y_fifo(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    for idx in range(10):
        manager.recibir_notificacion(_dto(idx, duracion_ms=4000))

    assert len(manager._visibles) == 3
    assert len(manager._queue) == 7


def test_auto_cierre_funciona(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.recibir_notificacion(_dto(1, duracion_ms=120))

    assert len(manager._visibles) == 1
    qtbot.wait(220)
    assert len(manager._visibles) == 0


def test_boton_cerrar_elimina_toast(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.recibir_notificacion(_dto(2, duracion_ms=4000))

    toast = next(iter(manager._visibles.values()))
    qtbot.mouseClick(toast._btn_cerrar, Qt.MouseButton.LeftButton)
    qtbot.wait(10)

    assert len(manager._visibles) == 0


def test_boton_detalles_abre_dialogo(qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.recibir_notificacion(_dto(3, detalles="stacktrace", correlacion_id="CID-1"))

    called = {"open": 0}

    def _fake_exec(self) -> int:
        called["open"] += 1
        return 0

    monkeypatch.setattr("app.ui.widgets.toast.DialogoDetallesNotificacion.exec", _fake_exec)

    toast = next(iter(manager._visibles.values()))
    qtbot.mouseClick(toast._btn_detalles, Qt.MouseButton.LeftButton)

    assert called["open"] == 1


def test_success_con_accion_no_crashea_y_ejecuta_callback(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    called = {"count": 0}

    def _action() -> None:
        called["count"] += 1

    manager.success("Mensaje", action_label="X", action_callback=_action)

    toast = next(iter(manager._visibles.values()))
    assert toast._btn_accion.isVisible()
    assert toast._btn_accion.text() == "X"

    qtbot.mouseClick(toast._btn_accion, Qt.MouseButton.LeftButton)

    assert called["count"] == 1


def test_success_sin_action_label_no_muestra_boton(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.success("Mensaje")

    toast = next(iter(manager._visibles.values()))
    assert not toast._btn_accion.isVisible()
