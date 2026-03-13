from __future__ import annotations

import pytest
from tests.ui.conftest import require_qt

require_qt()

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QMainWindow, QPushButton

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


def test_dedupe_actualiza_callback_y_accion_renderizada(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    called = {"first": 0, "second": 0}

    def _action_1() -> None:
        called["first"] += 1

    def _action_2() -> None:
        called["second"] += 1

    manager.warning("Mensaje inicial", code="D1", origin="origen.test", action_label="Primera", action_callback=_action_1)
    manager.warning("Mensaje nuevo", code="D1", origin="origen.test", action_label="Segunda", action_callback=_action_2)

    toast = next(iter(manager._visibles.values()))
    assert toast._btn_accion.text() == "Segunda"
    qtbot.mouseClick(toast._btn_accion, Qt.MouseButton.LeftButton)

    assert called["first"] == 0
    assert called["second"] == 1




def test_boton_cerrar_tiene_feedback_visual(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.recibir_notificacion(_dto(11, duracion_ms=4000))

    toast = next(iter(manager._visibles.values()))
    assert toast._btn_cerrar.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert toast._btn_cerrar.toolTip()
    estilos = toast.styleSheet()
    assert "toastCloseButton:hover" in estilos
    assert "toastCloseButton:pressed" in estilos
    assert "toastCloseButton:focus" in estilos

def test_cierre_manual_limpia_cache_y_modelo(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.info("Mensaje", code="M1", origin="origen.manual", duration_ms=4000)

    toast_id = next(iter(manager._visibles.keys()))
    toast = manager._visibles[toast_id]
    qtbot.mouseClick(toast._btn_cerrar, Qt.MouseButton.LeftButton)
    qtbot.wait(10)

    assert toast_id not in manager._cache
    assert toast_id not in manager._timers
    assert toast_id not in manager._visibles
    assert manager._modelo.listar() == []


def test_click_en_host_dispara_accion_toast(qtbot) -> None:
    window = QMainWindow()
    window.resize(900, 700)
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    called = {"count": 0}

    def _action() -> None:
        called["count"] += 1

    manager.success("Mensaje", action_label="Abrir", action_callback=_action, duration_ms=4000)

    toast = next(iter(manager._visibles.values()))
    posicion_en_host = toast._btn_accion.mapTo(window, toast._btn_accion.rect().center())
    qtbot.mouseClick(window, Qt.MouseButton.LeftButton, pos=posicion_en_host)

    assert called["count"] == 1


def test_actualizar_toast_agrega_boton_detalles_y_emite_id(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    manager.warning("Mensaje inicial", code="D1", origin="origen.test", details=None, duration_ms=4000)
    toast = next(iter(manager._visibles.values()))

    assert toast._btn_detalles is not None
    assert not toast._btn_detalles.isVisible()

    manager.warning("Mensaje con detalle", code="D1", origin="origen.test", details="trace", duration_ms=4000)

    assert toast._btn_detalles is not None
    assert toast._btn_detalles.isVisible()

    toast_ids: list[str] = []
    toast.solicitar_detalles.connect(toast_ids.append)
    qtbot.mouseClick(toast._btn_detalles, Qt.MouseButton.LeftButton)

    assert toast_ids == [toast.notificacion.id]


def test_actualizar_toast_no_duplica_boton_detalles(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    manager.warning("Mensaje", code="D2", origin="origen.test", details=None, duration_ms=4000)
    toast = next(iter(manager._visibles.values()))

    manager.warning("Mensaje", code="D2", origin="origen.test", details="detalle 1", duration_ms=4000)
    manager.warning("Mensaje", code="D2", origin="origen.test", details="detalle 2", duration_ms=4000)
    manager.warning("Mensaje", code="D2", origin="origen.test", details=None, duration_ms=4000)
    manager.warning("Mensaje", code="D2", origin="origen.test", details="detalle 3", duration_ms=4000)

    botones_detalles = toast.findChildren(type(toast._btn_cerrar), "toastDetailsButton")
    assert len(botones_detalles) == 1
    assert botones_detalles[0].isVisible()


def test_boton_accion_visible_y_habilitado_segun_contrato(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    manager.info("Mensaje", action_label="Reintentar", action_callback=None, duration_ms=4000)
    toast = next(iter(manager._visibles.values()))

    assert toast._btn_accion.isVisible()
    assert not toast._btn_accion.isEnabled()

    called = {"count": 0}

    def _accion() -> None:
        called["count"] += 1

    manager.info("Mensaje", action_label="Reintentar", action_callback=_accion, duration_ms=4000)

    assert toast._btn_accion.isVisible()
    assert toast._btn_accion.isEnabled()
    qtbot.mouseClick(toast._btn_accion, Qt.MouseButton.LeftButton)
    assert called["count"] == 1


def test_detalles_transicion_sin_con_sin_no_duplica(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    manager.warning("Mensaje", code="D3", origin="origen.test", details=None, duration_ms=4000)
    toast = next(iter(manager._visibles.values()))

    assert toast._btn_detalles is not None
    assert not toast._btn_detalles.isVisible()

    manager.warning("Mensaje", code="D3", origin="origen.test", details="detalle 1", duration_ms=4000)
    assert toast._btn_detalles.isVisible()

    manager.warning("Mensaje", code="D3", origin="origen.test", details=None, duration_ms=4000)
    assert not toast._btn_detalles.isVisible()

    botones_detalles = toast.findChildren(type(toast._btn_cerrar), "toastDetailsButton")
    assert len(botones_detalles) == 1

def test_detalles_emite_id_actual_tras_actualizaciones_consecutivas(qtbot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()

    manager = GestorToasts()
    manager.attach_to(window)

    manager.warning("Mensaje", code="D4", origin="origen.test", details="detalle 1", duration_ms=4000)
    toast = next(iter(manager._visibles.values()))

    ids_emitidos: list[str] = []
    toast.solicitar_detalles.connect(ids_emitidos.append)

    for idx in range(2, 5):
        manager.warning(
            "Mensaje",
            code="D4",
            origin="origen.test",
            details=f"detalle {idx}",
            duration_ms=4000,
        )
        assert toast.notificacion.id == "WARN:D4"
        qtbot.mouseClick(toast._btn_detalles, Qt.MouseButton.LeftButton)

    assert ids_emitidos == ["WARN:D4", "WARN:D4", "WARN:D4"]
    botones_detalles = toast.findChildren(type(toast._btn_cerrar), "toastDetailsButton")
    assert len(botones_detalles) == 1



def test_overlay_permite_click_en_host_fuera_de_tarjeta(qtbot) -> None:
    window = QMainWindow()
    window.resize(900, 700)
    qtbot.addWidget(window)

    boton_host = QPushButton("Host", window)
    boton_host.setObjectName("hostMainButton")
    boton_host.setGeometry(40, 640, 140, 32)

    clicks = {"count": 0}

    def _on_click() -> None:
        clicks["count"] += 1

    boton_host.clicked.connect(_on_click)

    window.show()

    manager = GestorToasts()
    manager.attach_to(window)
    manager.success("Mensaje", action_label="Abrir", action_callback=lambda: None, duration_ms=4000)

    assert len(manager._visibles) == 1

    posicion_global = boton_host.mapToGlobal(boton_host.rect().center())
    posicion_en_window = window.mapFromGlobal(posicion_global)
    qtbot.mouseClick(window, Qt.MouseButton.LeftButton, pos=posicion_en_window)

    assert clicks["count"] == 1
