from __future__ import annotations

from pathlib import Path

from app.entrypoints.post_login import ControladorSesionInterfaz, ejecutar_transicion_post_login


class _ErrorEsperado(RuntimeError):
    pass


def test_controlador_sesion_guarda_referencia() -> None:
    controlador = ControladorSesionInterfaz()
    ventana = object()

    assert controlador.guardar_ventana_principal(ventana) is True
    assert controlador.ventana_principal is ventana


def test_transicion_post_login_reintenta_sin_quit() -> None:
    eventos: list[tuple[str, dict[str, object]]] = []
    controlador = ControladorSesionInterfaz()
    intentos = {"total": 0}

    def crear() -> object:
        intentos["total"] += 1
        if intentos["total"] == 1:
            raise _ErrorEsperado("fallo inicial")
        return object()

    reintentos = {"total": 0}

    def informar_error(_error) -> bool:
        reintentos["total"] += 1
        return True

    assert (
        ejecutar_transicion_post_login(
            crear_ventana_principal=crear,
            registrar_ventana_principal=controlador.guardar_ventana_principal,
            mostrar_ventana_principal=lambda _window: None,
            registrar_evento=lambda accion, payload: eventos.append((accion, payload)),
            informar_error=informar_error,
        )
        is True
    )

    acciones = [accion for accion, _ in eventos]
    assert "post_login_transition_fail" in acciones
    assert acciones[-1] == "post_login_transition_ok"
    assert reintentos["total"] == 1
    assert controlador.ventana_principal is not None


def test_modulo_post_login_no_importa_sys_ni_quit() -> None:
    source = Path("app/entrypoints/post_login.py").read_text(encoding="utf-8")

    assert "import sys" not in source
    assert "sys.exit" not in source
    assert "QApplication.quit" not in source
