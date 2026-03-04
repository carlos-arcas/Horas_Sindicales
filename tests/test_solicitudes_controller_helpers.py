from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    SolicitudCrearPendientePeticion,
)
from app.ui.controllers.solicitudes_controller import (
    _construir_peticion_crear_pendiente,
    _mapear_error_persistencia_a_feedback,
    _normalizar_inputs_pendiente,
)


def _solicitud_base() -> SolicitudDTO:
    return SolicitudDTO(
        id=10,
        persona_id=5,
        fecha_solicitud="2026-02-01",
        fecha_pedida="2026-02-10",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=0.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
        generated=False,
    )


def test_normalizar_inputs_pendiente_con_valores_validos() -> None:
    solicitud = _solicitud_base()

    normalizada = _normalizar_inputs_pendiente(
        solicitud,
        horas=2.5,
        notas_texto="  nota de prueba  ",
    )

    assert normalizada.horas == 2.5
    assert normalizada.notas == "nota de prueba"
    assert solicitud.horas == 0.0
    assert solicitud.notas is None


def test_normalizar_inputs_pendiente_maneja_none_y_blancos() -> None:
    solicitud = _solicitud_base()

    sin_notas = _normalizar_inputs_pendiente(solicitud, horas=1.0, notas_texto=None)
    con_blancos = _normalizar_inputs_pendiente(solicitud, horas=1.0, notas_texto="   ")

    assert sin_notas.notas is None
    assert con_blancos.notas is None


def test_construir_peticion_y_mapear_error_persistencia() -> None:
    solicitud = _solicitud_base()

    peticion = _construir_peticion_crear_pendiente(solicitud, "corr-123")
    what, why, how = _mapear_error_persistencia_a_feedback(ValueError("fallo controlado"))

    assert isinstance(peticion, SolicitudCrearPendientePeticion)
    assert peticion.solicitud == solicitud
    assert peticion.correlation_id == "corr-123"
    assert what == "ui.solicitudes.no_se_guardo"
    assert why == "fallo controlado."
    assert how == "ui.solicitudes.corrige_formulario"
