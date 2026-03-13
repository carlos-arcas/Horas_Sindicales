from __future__ import annotations

import pytest

from app.ui.vistas.main_window.capacidades_opcionales import (
    CAPACIDAD_MODAL_SALDOS_DETALLE,
    RegistroCapacidadesOpcionales,
    capacidad_disponible,
    obtener_capacidad_opcional,
    registrar_capacidades_opcionales,
)


class VentanaFalsa:
    pass


def test_registro_capacidad_permite_registrar_obtener_y_verificar_disponibilidad() -> None:
    registro = RegistroCapacidadesOpcionales()

    registro.registrar(CAPACIDAD_MODAL_SALDOS_DETALLE, object)

    assert registro.obtener(CAPACIDAD_MODAL_SALDOS_DETALLE) is object
    assert registro.disponible(CAPACIDAD_MODAL_SALDOS_DETALLE) is True


def test_registrar_capacidades_opcionales_configura_registro_encapsulado_en_window() -> None:
    window = VentanaFalsa()

    registrar_capacidades_opcionales(window, {CAPACIDAD_MODAL_SALDOS_DETALLE: object})

    assert isinstance(window.registro_capacidades_opcionales, RegistroCapacidadesOpcionales)
    assert obtener_capacidad_opcional(window, CAPACIDAD_MODAL_SALDOS_DETALLE) is object
    assert capacidad_disponible(window, CAPACIDAD_MODAL_SALDOS_DETALLE) is True


def test_registro_capacidad_falla_rapido_si_nombre_capacidad_no_es_valido() -> None:
    registro = RegistroCapacidadesOpcionales()

    with pytest.raises(ValueError):
        registro.registrar("modal_saldos_detalle_typo", object)
