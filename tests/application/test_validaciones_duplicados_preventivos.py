from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import (
    detectar_duplicados_en_pendientes,
    normalizar_clave_pendiente,
)


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


def test_normalizar_clave_pendiente_homologa_fecha_y_tramo() -> None:
    dto = _solicitud(solicitud_id=1, fecha="2024-6-1", desde="9:0", hasta="11:0")

    assert normalizar_clave_pendiente(dto) == (1, "2024-06-01", "09:00", "11:00", "PARCIAL")


def test_detectar_duplicados_en_pendientes_devuelve_clave_duplicada() -> None:
    pendientes = [_solicitud(solicitud_id=1), _solicitud(solicitud_id=2)]

    duplicados = detectar_duplicados_en_pendientes(pendientes)

    assert duplicados == {(1, "2024-06-10", "10:00", "12:00", "PARCIAL")}


def test_detectar_duplicados_en_pendientes_ignora_sin_choque() -> None:
    pendientes = [_solicitud(solicitud_id=1), _solicitud(solicitud_id=2, desde="13:00", hasta="14:00")]

    assert detectar_duplicados_en_pendientes(pendientes) == set()
