from __future__ import annotations

from app.ui.vistas.main_window.acciones_personas import on_open_saldos_modal
from app.ui.vistas.main_window.capacidades_opcionales import CAPACIDAD_MODAL_SALDOS_DETALLE


class ToastFalso:
    def __init__(self) -> None:
        self.warning_calls: list[tuple[str, str | None]] = []
        self.error_calls: list[tuple[str, str | None]] = []

    def warning(self, mensaje: str, *, title: str | None = None) -> None:
        self.warning_calls.append((mensaje, title))

    def error(self, mensaje: str, *, title: str | None = None) -> None:
        self.error_calls.append((mensaje, title))


class DialogoSaldosFalso:
    def __init__(self, _window: object) -> None:
        self.exec_calls = 0

    def exec(self) -> None:
        self.exec_calls += 1


class VentanaFalsa:
    def __init__(self, dialogo_class: object | None) -> None:
        self.capacidades_opcionales = {CAPACIDAD_MODAL_SALDOS_DETALLE: dialogo_class} if dialogo_class else {}
        self.toast = ToastFalso()
        self._dialogo_saldos = None


def test_on_open_saldos_modal_ejecuta_dialogo_modal_y_guarda_referencia() -> None:
    window = VentanaFalsa(DialogoSaldosFalso)

    on_open_saldos_modal(window)

    assert isinstance(window._dialogo_saldos, DialogoSaldosFalso)
    assert window._dialogo_saldos.exec_calls == 1
    assert window.toast.warning_calls == []
    assert window.toast.error_calls == []


def test_on_open_saldos_modal_notifica_warning_si_modal_no_disponible() -> None:
    window = VentanaFalsa(None)

    on_open_saldos_modal(window)

    assert window._dialogo_saldos is None
    assert len(window.toast.warning_calls) == 1
    assert window.toast.error_calls == []


def test_on_open_saldos_modal_notifica_error_si_falla_apertura() -> None:
    class DialogoQueFalla:
        def __init__(self, _window: object) -> None:
            raise RuntimeError("boom")

    window = VentanaFalsa(DialogoQueFalla)

    on_open_saldos_modal(window)

    assert window._dialogo_saldos is None
    assert window.toast.warning_calls == []
    assert len(window.toast.error_calls) == 1
