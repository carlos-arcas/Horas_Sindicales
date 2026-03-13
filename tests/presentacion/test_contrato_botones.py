from __future__ import annotations

from app.ui.vistas.main_window.capacidades_opcionales import CAPACIDAD_MODAL_SALDOS_DETALLE
from app.ui.vistas.main_window.contrato_botones import (
    CONTRATOS_BOTONES_CRITICOS,
    aplicar_contrato_botones_criticos_runtime,
    validar_contrato_botones,
)


class BotonFalso:
    def __init__(self) -> None:
        self.habilitado = True
        self.tooltip = ""

    def setEnabled(self, valor: bool) -> None:
        self.habilitado = valor

    def setToolTip(self, valor: str) -> None:
        self.tooltip = valor


class VentanaFalsa:
    def __init__(self, *, incluir_saldos: bool = True) -> None:
        for contrato in CONTRATOS_BOTONES_CRITICOS:
            setattr(self, contrato.nombre_atributo_boton, BotonFalso())
            setattr(self, contrato.nombre_handler, lambda *args, **kwargs: None)
        self.capacidades_opcionales = {}
        if incluir_saldos:
            self.capacidades_opcionales[CAPACIDAD_MODAL_SALDOS_DETALLE] = object


def test_validar_contrato_botones_valido_sin_incidencias() -> None:
    atributos = {contrato.nombre_atributo_boton for contrato in CONTRATOS_BOTONES_CRITICOS}
    handlers = {contrato.nombre_handler for contrato in CONTRATOS_BOTONES_CRITICOS}

    incidencias = validar_contrato_botones(atributos, handlers)

    assert incidencias == []


def test_validar_contrato_botones_detecta_boton_faltante() -> None:
    contratos = list(CONTRATOS_BOTONES_CRITICOS)
    boton_faltante = contratos[0].nombre_atributo_boton
    atributos = {contrato.nombre_atributo_boton for contrato in contratos if contrato.nombre_atributo_boton != boton_faltante}
    handlers = {contrato.nombre_handler for contrato in contratos}

    incidencias = validar_contrato_botones(atributos, handlers)

    assert any(incidencia.tipo == "boton_no_existente" and incidencia.nombre_atributo_boton == boton_faltante for incidencia in incidencias)


def test_validar_contrato_botones_detecta_handler_faltante() -> None:
    contratos = list(CONTRATOS_BOTONES_CRITICOS)
    handler_faltante = contratos[0].nombre_handler
    atributos = {contrato.nombre_atributo_boton for contrato in contratos}
    handlers = {contrato.nombre_handler for contrato in contratos if contrato.nombre_handler != handler_faltante}

    incidencias = validar_contrato_botones(atributos, handlers)

    assert any(incidencia.tipo == "handler_no_existente" and incidencia.nombre_handler == handler_faltante for incidencia in incidencias)


def test_aplicar_contrato_deshabilita_boton_si_falta_dependencia_opcional() -> None:
    window = VentanaFalsa(incluir_saldos=False)

    aplicar_contrato_botones_criticos_runtime(window)

    assert window.open_saldos_modal_button.habilitado is False
    assert "disponible" in window.open_saldos_modal_button.tooltip.lower()



def test_aplicar_contrato_mantiene_boton_saldos_habilitado_si_dependencia_esta_disponible() -> None:
    window = VentanaFalsa(incluir_saldos=True)

    aplicar_contrato_botones_criticos_runtime(window)

    assert window.open_saldos_modal_button.habilitado is True
    assert window.open_saldos_modal_button.tooltip == ""


def test_aplicar_contrato_saldos_no_depende_de_atributo_magico_privado() -> None:
    window = VentanaFalsa(incluir_saldos=True)
    window._saldos_dialog_class = None

    aplicar_contrato_botones_criticos_runtime(window)

    assert window.open_saldos_modal_button.habilitado is True
