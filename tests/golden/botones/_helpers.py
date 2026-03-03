from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.utilidades.event_recorder import EventRecorder
from tests.utilidades.normalizar_reportes import guardar_golden


def install_pyside6_stubs() -> None:
    for key in ["PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui"]:
        sys.modules.pop(key, None)

    qtcore = types.ModuleType("PySide6.QtCore")

    class QObject:  # noqa: D401
        def moveToThread(self, _thread: Any) -> None:
            return None

        def deleteLater(self, *_args: Any) -> None:
            return None

    class QThread:
        def __init__(self) -> None:
            self.started = _SignalImpl()
            self.finished = _SignalImpl()

        def start(self, *_args: Any) -> None:
            self.started.emit()

        def quit(self, *_args: Any) -> None:
            self.finished.emit()

        def deleteLater(self, *_args: Any) -> None:
            return None

    class Signal:
        def __init__(self, *_: Any) -> None:
            self._handlers: list[Any] = []

        def connect(self, callback: Any) -> None:
            self._handlers.append(callback)

        def emit(self, *args: Any) -> None:
            for handler in list(self._handlers):
                handler(*args)

    def Slot(*_: Any, **__: Any):
        def decorator(func: Any) -> Any:
            return func

        return decorator

    class QDate:
        @staticmethod
        def currentDate() -> "QDate":
            return QDate()

        def addDays(self, _days: int) -> "QDate":
            return self

    class QItemSelectionModel:
        class SelectionFlag:
            Select = 1
            Deselect = 2
            Rows = 4

    qtcore.QObject = QObject
    qtcore.QThread = QThread
    qtcore.Signal = Signal
    qtcore.Slot = Slot
    qtcore.QDate = QDate
    qtcore.QItemSelectionModel = QItemSelectionModel
    qtcore.Qt = type("Qt", (), {})
    qtcore.__getattr__ = lambda name: _dummy_class(name)


    def _dummy_class(name: str):
        return type(name, (), {"__init__": lambda self, *a, **k: None})

    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtwidgets.__getattr__ = lambda name: _dummy_class(name)
    qtgui = types.ModuleType("PySide6.QtGui")
    qtgui.__getattr__ = lambda name: _dummy_class(name)

    pyside6 = types.ModuleType("PySide6")
    pyside6.QtCore = qtcore
    pyside6.QtWidgets = qtwidgets
    pyside6.QtGui = qtgui
    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules["PySide6.QtGui"] = qtgui


class _SignalImpl:
    def __init__(self) -> None:
        self._handlers: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._handlers.append(callback)

    def emit(self, *args: Any) -> None:
        for handler in list(self._handlers):
            handler(*args)


class FakeToast:
    def __init__(self, recorder: EventRecorder) -> None:
        self._recorder = recorder

    def warning(self, message: str, title: str | None = None, **_kwargs: Any) -> None:
        self._recorder.record("validacion_mostrada", {"clave_i18n": message})
        self._recorder.record("toast_mostrado", {"tipo": "warning", "clave": message, "titulo": title or ""})


class FakeNotifications:
    def __init__(self, recorder: EventRecorder) -> None:
        self._recorder = recorder

    def notify_operation(self, feedback: Any) -> None:
        self._recorder.record("toast_mostrado", {"tipo": "operation", "titulo": getattr(feedback, "title", "")})


class FakeButton:
    def __init__(self, recorder: EventRecorder, name: str) -> None:
        self._recorder = recorder
        self._name = name

    def setEnabled(self, value: bool) -> None:
        self._recorder.record("estado_ui_cambiado", {"clave": f"{self._name}.enabled", "valor": value})

    def setText(self, value: str) -> None:
        self._recorder.record("estado_ui_cambiado", {"clave": f"{self._name}.text", "valor": value})


class FakeTable:
    def __init__(self, recorder: EventRecorder, name: str) -> None:
        self._recorder = recorder
        self._name = name

    def clearSelection(self) -> None:
        self._recorder.record("estado_ui_cambiado", {"clave": f"{self._name}.selection", "valor": "cleared"})


class FakeSolicitudUseCases:
    def __init__(self, recorder: EventRecorder) -> None:
        self._recorder = recorder

    def buscar_conflicto_pendiente(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def calcular_minutos_solicitud(self, _solicitud: Any) -> int:
        return 60

    def crear_solicitud(self, solicitud: Any, *, correlation_id: str | None = None) -> Any:
        self._recorder.record(
            "use_case_llamado",
            {"nombre": "crear_solicitud", "payload_minimo": {"correlation_id": correlation_id or "", "fecha": getattr(solicitud, "fecha_pedida", "")}},
        )
        return solicitud

    def eliminar_solicitud(self, solicitud_id: int, correlation_id: str | None = None) -> None:
        self._recorder.record(
            "use_case_llamado",
            {"nombre": "eliminar_solicitud", "payload_minimo": {"solicitud_id": solicitud_id, "correlation_id": correlation_id or ""}},
        )


@dataclass
class FakeSolicitud:
    fecha_pedida: str = "2026-01-10"
    completo: bool = False
    notas: str = ""
    id: int | None = None

    def model_copy(self, update: dict[str, Any]) -> "FakeSolicitud":
        data = {"fecha_pedida": self.fecha_pedida, "completo": self.completo, "notas": self.notas, "id": self.id}
        data.update(update)
        return FakeSolicitud(**data)


def assert_matches_golden(test_file: Path, golden_name: str, actual_json: str) -> None:
    golden_path = test_file.parent / f"{golden_name}.json"
    if os.getenv("UPDATE_GOLDEN") == "1":
        guardar_golden(golden_path, actual_json)
    expected = golden_path.read_text(encoding="utf-8")
    assert actual_json == expected
