from __future__ import annotations

from app.entrypoints.arranque_hilo import TrabajadorArranque


class _TraductorDummy:
    def __call__(self, key: str, **kwargs) -> str:
        return key.format(**kwargs) if kwargs else key


def test_worker_arranque_emite_failed_si_lectura_config_falla(monkeypatch) -> None:
    worker = TrabajadorArranque(traducir=_TraductorDummy())
    capturas: list[tuple[str, str, str]] = []

    def _fallar_arranque_puro():
        raise RuntimeError("boom-test")

    monkeypatch.setattr("app.entrypoints.arranque_hilo.ejecutar_arranque_puro", _fallar_arranque_puro)
    worker.failed.connect(lambda incident_id, mensaje, detalles: capturas.append((incident_id, mensaje, detalles)))

    worker.run()

    assert capturas
    incident_id, mensaje, detalles = capturas[0]
    assert incident_id.startswith("INC-BOOT-")
    assert mensaje == "startup_error_dialog_message"
    assert "boom-test" in detalles
