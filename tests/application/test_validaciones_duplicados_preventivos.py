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


def test_un_solo_pendiente_no_es_duplicado_si_es_el_mismo_en_edicion() -> None:
    pendiente = _solicitud(solicitud_id=10)

    assert not hay_duplicado_distinto(pendiente, [pendiente], excluir_por_id=10, excluir_por_indice=0)


def test_dos_pendientes_misma_clave_distinto_id_es_duplicado() -> None:
    candidato = _solicitud(solicitud_id=None)
    existente = _solicitud(solicitud_id=11)

    assert hay_duplicado_distinto(candidato, [existente])


def test_editar_pendiente_mismo_id_no_dispara_duplicado() -> None:
    editada = _solicitud(solicitud_id=22)
    otra = _solicitud(solicitud_id=23, desde="13:00", hasta="14:00")

    assert not hay_duplicado_distinto(editada, [editada, otra], excluir_por_id=22, excluir_por_indice=0)


def test_formulario_igual_a_pendiente_solo_duplica_si_intenta_anadir() -> None:
    existente = _solicitud(solicitud_id=44)
    formulario = _solicitud(solicitud_id=None)

    assert hay_duplicado_distinto(formulario, [existente])
    assert not hay_duplicado_distinto(formulario, [existente], excluir_por_id=44, excluir_por_indice=0)
