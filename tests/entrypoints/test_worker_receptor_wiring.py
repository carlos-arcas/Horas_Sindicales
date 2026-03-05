from __future__ import annotations

from app.entrypoints.ui_main import conectar_senales_arranque_a_receptor


class FakeSignal:
    def __init__(self) -> None:
        self.llamadas: list[tuple[object, object]] = []

    def connect(self, slot, tipo=None) -> None:
        self.llamadas.append((slot, tipo))


class FakeWorker:
    def __init__(self) -> None:
        self.finished = FakeSignal()
        self.failed = FakeSignal()


class FakeReceptor:
    def recibir_ok(self, _payload) -> None:
        return None

    def recibir_error(self, _payload) -> None:
        return None


class _QtFalso:
    QueuedConnection = object()


def test_conectar_senales_arranque_a_receptor_usa_solo_conexiones_permitidas() -> None:
    worker = FakeWorker()
    receptor = FakeReceptor()

    conectar_senales_arranque_a_receptor(worker, receptor, _QtFalso)

    assert worker.finished.llamadas == [(receptor.recibir_ok, _QtFalso.QueuedConnection)]
    assert worker.failed.llamadas == [(receptor.recibir_error, _QtFalso.QueuedConnection)]
