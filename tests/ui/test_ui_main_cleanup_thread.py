from __future__ import annotations

from app.entrypoints import ui_main


class _ThreadEliminado:
    def isRunning(self) -> bool:
        raise RuntimeError("Internal C++ object (QThread) already deleted")

    def quit(self) -> None:
        raise AssertionError("quit no debe ejecutarse")

    def wait(self, _timeout: int) -> None:
        raise AssertionError("wait no debe ejecutarse")


def test_cleanup_thread_ignora_qthread_eliminado() -> None:
    ui_main._cleanup_startup_thread_seguro(_ThreadEliminado())
