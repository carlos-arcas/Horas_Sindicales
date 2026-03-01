from __future__ import annotations

from app.entrypoints.arranque_hilo import TrabajadorArranque
from presentacion.i18n import I18nManager


class _DummyContainer:
    repositorio_preferencias = object()


def test_worker_arranque_emite_failed_si_build_container_falla(monkeypatch) -> None:
    i18n = I18nManager("es")
    worker = TrabajadorArranque(container_seed=None, i18n=i18n)
    capturas: list[tuple[str, str, str]] = []

    def _fallar_container():
        raise RuntimeError("boom-test")

    monkeypatch.setattr("app.bootstrap.container.build_container", _fallar_container)
    worker.failed.connect(lambda incident_id, mensaje, detalles: capturas.append((incident_id, mensaje, detalles)))

    worker.run()

    assert capturas
    incident_id, mensaje, detalles = capturas[0]
    assert incident_id.startswith("INC-BOOT-")
    assert mensaje == i18n.t("startup_error_dialog_message")
    assert "boom-test" in detalles
