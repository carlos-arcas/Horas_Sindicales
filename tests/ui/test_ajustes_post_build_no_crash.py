from __future__ import annotations

from app.ui.vistas.main_window.ajustes_post_build import (
    actualizar_columnas_responsivas,
    configurar_placeholders_hora,
    normalizar_alturas_inputs,
)
from app.ui.vistas.main_window.mixins.ajustes_post_build_mixin import AjustesPostBuildMixin
from app.ui.vistas.main_window.mixins.handlers_formulario_solicitud_mixin import (
    HandlersFormularioSolicitudMixin,
)


class _SizeHint:
    def __init__(self, height: int) -> None:
        self._height = height

    def height(self) -> int:
        return self._height


class _FakeInput:
    def __init__(self) -> None:
        self.placeholder = ""
        self.minimum_height = 0

    def setPlaceholderText(self, value: str) -> None:
        self.placeholder = value

    def setMinimumHeight(self, value: int) -> None:
        self.minimum_height = value

    def sizeHint(self) -> _SizeHint:
        return _SizeHint(28)


class _FakeHeader:
    def __init__(self) -> None:
        self.stretch = False

    def setStretchLastSection(self, value: bool) -> None:
        self.stretch = value


class _FakeTable:
    def __init__(self) -> None:
        self.header = _FakeHeader()

    def horizontalHeader(self) -> _FakeHeader:
        return self.header


class _FakeToast:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)


class _FakeButton:
    def __init__(self) -> None:
        self.clicked = False

    def isEnabled(self) -> bool:
        return True

    def click(self) -> None:
        self.clicked = True


class _FakeController:
    def __init__(self) -> None:
        self.add_called = False
        self.confirm_called = False

    def on_add_pendiente(self) -> None:
        self.add_called = True

    def on_confirmar(self) -> None:
        self.confirm_called = True


class _WindowAjustes(AjustesPostBuildMixin):
    def __init__(self) -> None:
        self.desde_input = _FakeInput()
        self.hasta_input = _FakeInput()
        self.fecha_input = _FakeInput()
        self.persona_combo = _FakeInput()
        self.pending_table = _FakeTable()
        self.historico_table = _FakeTable()


class _WindowHandlers(HandlersFormularioSolicitudMixin):
    def __init__(self) -> None:
        self.toast = _FakeToast()
        self._solicitudes_controller = _FakeController()
        self.agregar_button = _FakeButton()
        self.preview_updates = 0
        self.validation_updates = 0

    def _update_action_state(self) -> None:
        self.preview_updates += 1

    def _schedule_preventive_validation(self) -> None:
        self.validation_updates += 1


def test_funciones_post_build_no_crash_con_window_fake() -> None:
    window = _WindowAjustes()

    configurar_placeholders_hora(window)
    actualizar_columnas_responsivas(window)
    normalizar_alturas_inputs(window)

    assert window.desde_input.placeholder
    assert window.hasta_input.placeholder
    assert window.pending_table.header.stretch is True
    assert window.historico_table.header.stretch is True
    assert window.fecha_input.minimum_height >= 32


def test_mixins_post_build_y_handlers_minimos_no_crash() -> None:
    ajustes = _WindowAjustes()
    ajustes._configure_time_placeholders()
    ajustes._update_responsive_columns()
    ajustes._normalize_input_heights()

    handlers = _WindowHandlers()
    handlers._on_fecha_changed()
    handlers._on_completo_changed(True)
    handlers._on_add_pendiente()
    handlers._on_confirmar()

    assert handlers.preview_updates == 2
    assert handlers.validation_updates == 2
    assert handlers._solicitudes_controller.add_called is True
    assert handlers._solicitudes_controller.confirm_called is True
