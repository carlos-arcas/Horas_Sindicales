from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import hay_duplicado_distinto


def _solicitud(
    *,
    solicitud_id: int | None,
    persona_id: int = 1,
    fecha: str = "2024-06-10",
    desde: str | None = "10:00",
    hasta: str | None = "12:00",
    completo: bool = False,
) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_un_pendiente_form_igual_modo_actualizar_no_es_duplicado() -> None:
    pendiente = _solicitud(solicitud_id=10)

    assert not hay_duplicado_distinto(
        pendiente,
        [pendiente],
        excluir_por_id=10,
        excluir_por_indice=0,
    )


def test_un_pendiente_form_igual_modo_anadir_si_es_duplicado() -> None:
    pendiente = _solicitud(solicitud_id=10)
    formulario = _solicitud(solicitud_id=None)

    assert hay_duplicado_distinto(formulario, [pendiente])


def test_dos_pendientes_iguales_es_duplicado_siempre() -> None:
    pendiente_a = _solicitud(solicitud_id=10)
    pendiente_b = _solicitud(solicitud_id=11)

    assert hay_duplicado_distinto(_solicitud(solicitud_id=None), [pendiente_a, pendiente_b])


def test_dos_pendientes_distintas_no_es_duplicado() -> None:
    pendiente_a = _solicitud(solicitud_id=10)
    pendiente_b = _solicitud(solicitud_id=11, desde="13:00", hasta="14:00")

    assert not hay_duplicado_distinto(_solicitud(solicitud_id=None, desde="15:00", hasta="16:00"), [pendiente_a, pendiente_b])


def test_edicion_de_a_con_b_igual_si_es_duplicado_por_existir_otra() -> None:
    pendiente_a = _solicitud(solicitud_id=10)
    pendiente_b = _solicitud(solicitud_id=11)
    formulario = _solicitud(solicitud_id=10)

    assert hay_duplicado_distinto(
        formulario,
        [pendiente_a, pendiente_b],
        excluir_por_id=10,
        excluir_por_indice=0,
    )
