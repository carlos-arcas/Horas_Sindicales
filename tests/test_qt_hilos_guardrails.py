from __future__ import annotations

import logging

import pytest

from app.ui import qt_hilos


class _ThreadToken:
    pass


class _AppFake:
    def __init__(self, thread_token: object) -> None:
        self._thread_token = thread_token

    def thread(self) -> object:
        return self._thread_token


class _QApplicationFake:
    _instance: object | None = None

    @classmethod
    def instance(cls) -> object | None:
        return cls._instance


class _QThreadFake:
    _current: object | None = None

    @staticmethod
    def currentThread() -> object | None:
        return _QThreadFake._current


class _QTimerFake:
    llamadas: list[tuple[int, object]] = []

    @staticmethod
    def singleShot(delay: int, fn) -> None:
        _QTimerFake.llamadas.append((delay, fn))


def _configurar_qt_falso(monkeypatch: pytest.MonkeyPatch, *, es_ui: bool) -> None:
    thread_ui = _ThreadToken()
    _QApplicationFake._instance = _AppFake(thread_ui)
    _QThreadFake._current = thread_ui if es_ui else _ThreadToken()
    _QTimerFake.llamadas = []
    monkeypatch.setattr(qt_hilos, "QApplication", _QApplicationFake)
    monkeypatch.setattr(qt_hilos, "QThread", _QThreadFake)
    monkeypatch.setattr(qt_hilos, "QTimer", _QTimerFake)


def test_assert_hilo_ui_o_log_lanza_en_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=False)
    monkeypatch.setenv("CI", "true")

    with pytest.raises(AssertionError, match="contexto_prueba"):
        qt_hilos.assert_hilo_ui_o_log("contexto_prueba", logging.getLogger(__name__))


def test_assert_hilo_ui_o_log_solo_log_en_runtime(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=False)
    monkeypatch.delenv("CI", raising=False)

    with caplog.at_level(logging.ERROR):
        qt_hilos.assert_hilo_ui_o_log("contexto_runtime", logging.getLogger("tests"))

    assert "UI_THREAD_ASSERT" in caplog.text


def test_ejecutar_en_hilo_ui_encola_cuando_no_es_hilo_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=False)
    ejecutada = {"ok": False}

    qt_hilos.ejecutar_en_hilo_ui(
        lambda: ejecutada.__setitem__("ok", True),
        contexto="dispatch_prueba",
        logger=logging.getLogger("tests"),
    )

    assert not ejecutada["ok"]
    assert len(_QTimerFake.llamadas) == 1
    assert _QTimerFake.llamadas[0][0] == 0


def test_ejecutar_en_hilo_ui_ejecuta_directo_en_hilo_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=True)
    ejecutada = {"ok": False}

    qt_hilos.ejecutar_en_hilo_ui(
        lambda: ejecutada.__setitem__("ok", True),
        contexto="directo_prueba",
        logger=logging.getLogger("tests"),
    )

    assert ejecutada["ok"]
    assert not _QTimerFake.llamadas


def test_comparar_threads_devuelve_true_solo_si_es_misma_referencia() -> None:
    hilo = _ThreadToken()

    assert qt_hilos.comparar_threads(hilo, hilo) is True
    assert qt_hilos.comparar_threads(_ThreadToken(), _ThreadToken()) is False


def test_asegurar_en_hilo_ui_lanza_y_loguea_violation(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=False)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            qt_hilos.asegurar_en_hilo_ui(lambda: None)

    assert "UI_QT_THREAD_VIOLATION" in caplog.text


def test_asegurar_en_hilo_ui_no_lanza_en_hilo_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    _configurar_qt_falso(monkeypatch, es_ui=True)

    qt_hilos.asegurar_en_hilo_ui(lambda: None)


def test_derivar_nombre_operacion_con_callable_devuelve_qualname() -> None:
    def funcion_prueba() -> None:
        return

    assert qt_hilos.derivar_nombre_operacion(funcion_prueba) == funcion_prueba.__qualname__


def test_derivar_nombre_operacion_sin_qualname_devuelve_none() -> None:
    assert qt_hilos.derivar_nombre_operacion(object()) is None
