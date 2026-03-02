from __future__ import annotations

from app.entrypoints.arranque_hilo import TrabajadorArranque


class _DummyContainer:
    repositorio_preferencias = object()


def test_worker_arranque_emite_failed_si_build_container_falla(monkeypatch) -> None:
    worker = TrabajadorArranque(container_seed=None)
    capturas: list[tuple[str, str, str]] = []

    def _fallar_container():
        raise RuntimeError("boom-test")

    monkeypatch.setattr("app.bootstrap.container.build_container", _fallar_container)
    worker.failed.connect(
        lambda incident_id, mensaje, detalles: capturas.append(
            (incident_id, mensaje, detalles)
        )
    )

    worker.run()

    assert capturas
    incident_id, mensaje, detalles = capturas[0]
    assert incident_id.startswith("INC-BOOT-")
    assert mensaje == "startup_error_dialog_message"
    assert "boom-test" in detalles
