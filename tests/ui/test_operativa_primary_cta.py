from types import SimpleNamespace

from app.ui.main_window import MainWindow


class _WidgetStub:
    def __init__(self) -> None:
        self.enabled = None
        self.text = ""
        self.tooltip = ""

    def setEnabled(self, value: bool) -> None:
        self.enabled = value

    def setText(self, text: str) -> None:
        self.text = text

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


def _window_stub(*, form_valid: bool, form_message: str, selected_pending: list[int], pending_count: int = 0) -> SimpleNamespace:
    stepper = [_WidgetStub(), _WidgetStub(), _WidgetStub()]
    return SimpleNamespace(
        _current_persona=lambda: object(),
        _validate_solicitud_form=lambda: (form_valid, form_message),
        _pending_solicitudes=[object()] * pending_count,
        _pending_conflict_rows=set(),
        _pending_view_all=False,
        _selected_pending_solicitudes=lambda: selected_pending,
        _selected_historico_solicitudes=lambda: [],
        _set_operativa_step=lambda _step: None,
        agregar_button=_WidgetStub(),
        insertar_sin_pdf_button=_WidgetStub(),
        confirmar_button=_WidgetStub(),
        edit_persona_button=_WidgetStub(),
        delete_persona_button=_WidgetStub(),
        edit_grupo_button=_WidgetStub(),
        editar_pdf_button=_WidgetStub(),
        eliminar_button=_WidgetStub(),
        eliminar_pendiente_button=_WidgetStub(),
        ver_detalle_button=_WidgetStub(),
        resync_historico_button=_WidgetStub(),
        generar_pdf_button=_WidgetStub(),
        stepper_labels=stepper,
        primary_cta_button=_WidgetStub(),
        primary_cta_hint=_WidgetStub(),
    )


def test_operativa_primary_cta_prioritiza_anadir_con_formulario_valido() -> None:
    window = _window_stub(form_valid=True, form_message="", selected_pending=[], pending_count=0)

    MainWindow._update_action_state(window)

    assert window.primary_cta_button.text == "Añadir a pendientes"
    assert window.primary_cta_button.enabled is True
    assert window.primary_cta_hint.text == ""


def test_operativa_primary_cta_prioritiza_confirmar_si_hay_seleccion() -> None:
    window = _window_stub(form_valid=True, form_message="", selected_pending=[1], pending_count=2)

    MainWindow._update_action_state(window)

    assert window.primary_cta_button.text == "Confirmar seleccionadas"
    assert window.primary_cta_button.enabled is True


def test_operativa_primary_cta_bloqueado_con_error_validacion() -> None:
    window = _window_stub(
        form_valid=False,
        form_message="La hora de fin debe ser posterior a la de inicio.",
        selected_pending=[1],
        pending_count=2,
    )

    MainWindow._update_action_state(window)

    assert window.primary_cta_button.text == "Confirmar seleccionadas"
    assert window.primary_cta_button.enabled is False
    assert window.primary_cta_hint.text == "La hora de fin debe ser posterior a la de inicio."
