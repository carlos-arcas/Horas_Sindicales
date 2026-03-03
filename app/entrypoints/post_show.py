from __future__ import annotations

from typing import Callable


def _try_call(callable_obj: object) -> None:
    if callable(callable_obj):
        callable_obj()


def preparar_mostrar_ventana(
    *,
    window: object,
    splash: object | None,
    scheduler: Callable[[Callable[[], None]], None],
    marcar_stage: Callable[[str], None],
) -> None:
    window.show()

    def _focus_boost() -> None:
        try:
            raise_window = window.raise_
        except AttributeError:
            raise_window = None
        _try_call(raise_window)

        try:
            activate_window = window.activateWindow
        except AttributeError:
            activate_window = None
        _try_call(activate_window)

    _focus_boost()
    scheduler(_focus_boost)
    marcar_stage("ui.mainwindow.mostrada")

    if splash is None:
        return

    try:
        close_splash = splash.close
    except AttributeError:
        close_splash = None
    if callable(close_splash):
        close_splash()
        marcar_stage("ui.splash.cerrado")


def programar_post_init(
    *,
    window: object,
    scheduler: Callable[[Callable[[], None]], None],
    marcar_stage: Callable[[str], None],
) -> None:
    try:
        if window._post_init_programado:
            return
    except AttributeError:
        pass

    window._post_init_programado = True
    marcar_stage("ui.post_init.programado")

    def _run_post_init() -> None:
        marcar_stage("ui.post_init.iniciado")
        try:
            post_init_load = window._post_init_load
        except AttributeError:
            return
        if callable(post_init_load):
            post_init_load()

    scheduler(_run_post_init)

