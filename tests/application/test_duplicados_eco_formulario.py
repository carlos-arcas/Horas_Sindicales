from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import detectar_duplicados_en_pendientes


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


def test_pendientes_unica_igual_al_formulario_no_cuenta_como_duplicado_en_pendientes() -> None:
    pendiente = _solicitud(solicitud_id=10)
    formulario = _solicitud(solicitud_id=None)

    assert formulario == _solicitud(solicitud_id=None)
    assert detectar_duplicados_en_pendientes([pendiente]) == set()


def test_pendientes_dos_iguales_si_cuenta_como_duplicado_en_pendientes() -> None:
    pendiente_a = _solicitud(solicitud_id=10)
    pendiente_b = _solicitud(solicitud_id=11)

    assert len(detectar_duplicados_en_pendientes([pendiente_a, pendiente_b])) == 1


def test_pendientes_diferentes_no_cuenta_como_duplicado_en_pendientes() -> None:
    pendiente_a = _solicitud(solicitud_id=10)
    pendiente_b = _solicitud(solicitud_id=11, desde="13:00", hasta="14:00")

    assert detectar_duplicados_en_pendientes([pendiente_a, pendiente_b]) == set()


def test_edicion_no_excluye_duplicados_reales_si_ambas_filas_siguen_en_caja() -> None:
    pendiente_editing = _solicitud(solicitud_id=10)
    pendiente_otra = _solicitud(solicitud_id=11)

    assert len(detectar_duplicados_en_pendientes([pendiente_editing, pendiente_otra])) == 1
