from __future__ import annotations

from app.entrypoints.post_show import preparar_mostrar_ventana, programar_post_init


class FakeWindow:
    def __init__(self, log: list[str] | None = None) -> None:
        self.calls: list[str] = []
        self.post_init_calls = 0
        self.log = log

    def show(self) -> None:
        self.calls.append("show")
        if self.log is not None:
            self.log.append("show")

    def raise_(self) -> None:
        self.calls.append("raise")
        if self.log is not None:
            self.log.append("raise")

    def activateWindow(self) -> None:  # noqa: N802 - Qt API name
        self.calls.append("activate")
        if self.log is not None:
            self.log.append("activate")

    def _post_init_load(self) -> None:
        self.post_init_calls += 1


class FakeSplash:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def close(self) -> None:
        self._calls.append("close")


def test_preparar_mostrar_ventana_show_antes_de_cerrar_splash() -> None:
    call_order: list[str] = []
    window = FakeWindow(call_order)
    splash = FakeSplash(call_order)
    stages: list[str] = []
    cola: list[callable] = []

    def scheduler(fn):
        cola.append(fn)

    preparar_mostrar_ventana(
        window=window,
        splash=splash,
        scheduler=scheduler,
        marcar_stage=stages.append,
    )

    assert window.calls[0] == "show"
    assert call_order.index("show") < call_order.index("close")
    assert "ui.mainwindow.mostrada" in stages
    assert "ui.splash.cerrado" in stages
    assert len(cola) == 1



def test_programar_post_init_es_idempotente_y_diferido() -> None:
    window = FakeWindow()
    stages: list[str] = []
    cola: list[callable] = []

    def scheduler(fn):
        cola.append(fn)

    programar_post_init(window=window, scheduler=scheduler, marcar_stage=stages.append)
    programar_post_init(window=window, scheduler=scheduler, marcar_stage=stages.append)

    assert len(cola) == 1
    assert window.post_init_calls == 0
    assert stages.count("ui.post_init.programado") == 1

    cola[0]()

    assert window.post_init_calls == 1
    assert "ui.post_init.iniciado" in stages
