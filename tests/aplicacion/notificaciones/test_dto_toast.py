from __future__ import annotations

from datetime import datetime

import pytest

from aplicacion.notificaciones.dto_toast import NivelToast, NotificacionToastDTO


def test_dto_valido_se_crea_correctamente() -> None:
    toast = NotificacionToastDTO(
        nivel=NivelToast.SUCCESS,
        titulo="Guardado",
        mensaje="Cambios guardados con éxito",
        detalles="Detalle opcional",
        codigo="SAVE_OK",
        correlacion_id="corr-123",
        duracion_ms=3000,
    )

    assert toast.nivel is NivelToast.SUCCESS
    assert toast.titulo == "Guardado"
    assert toast.mensaje == "Cambios guardados con éxito"
    assert toast.detalles == "Detalle opcional"
    assert toast.codigo == "SAVE_OK"
    assert toast.correlacion_id == "corr-123"
    assert toast.duracion_ms == 3000


def test_titulo_vacio_lanza_value_error() -> None:
    with pytest.raises(ValueError, match="titulo"):
        NotificacionToastDTO(
            nivel=NivelToast.INFO,
            titulo="   ",
            mensaje="Mensaje válido",
        )


def test_mensaje_vacio_lanza_value_error() -> None:
    with pytest.raises(ValueError, match="mensaje"):
        NotificacionToastDTO(
            nivel=NivelToast.INFO,
            titulo="Título válido",
            mensaje="",
        )


def test_duracion_negativa_lanza_value_error() -> None:
    with pytest.raises(ValueError, match="duracion_ms"):
        NotificacionToastDTO(
            nivel=NivelToast.WARNING,
            titulo="Título válido",
            mensaje="Mensaje válido",
            duracion_ms=-1,
        )


def test_id_y_timestamp_se_generan_automaticamente() -> None:
    toast = NotificacionToastDTO(
        nivel=NivelToast.ERROR,
        titulo="Error",
        mensaje="Se produjo un error",
    )

    assert isinstance(toast.id, str)
    assert toast.id
    assert isinstance(toast.timestamp, datetime)


def test_valores_por_defecto_correctos() -> None:
    toast = NotificacionToastDTO(
        nivel=NivelToast.INFO,
        titulo="Info",
        mensaje="Mensaje",
    )

    assert toast.detalles is None
    assert toast.codigo is None
    assert toast.correlacion_id is None
    assert toast.duracion_ms == 8000
