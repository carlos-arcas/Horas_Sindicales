from __future__ import annotations

from types import SimpleNamespace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.detector_duplicados import detectar_duplicado


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


def test_detector_duplicado_parcial() -> None:
    actual = _solicitud(solicitud_id=None, desde="10:00", hasta="11:00")
    existentes = [_solicitud(solicitud_id=1, desde="10:30", hasta="11:30")]

    assert detectar_duplicado(actual, existentes).hay_duplicado is True


def test_detector_duplicado_completo() -> None:
    actual = _solicitud(solicitud_id=None, completo=True, desde=None, hasta=None)
    existentes = [_solicitud(solicitud_id=1, desde="18:00", hasta="19:00")]

    assert detectar_duplicado(actual, existentes).hay_duplicado is True


def test_detector_no_solape_en_borde_semiabierto() -> None:
    actual = _solicitud(solicitud_id=None, desde="17:00", hasta="18:00")
    existentes = [_solicitud(solicitud_id=1, desde="18:00", hasta="19:00")]

    assert detectar_duplicado(actual, existentes).hay_duplicado is False


def test_detector_ignora_eliminados() -> None:
    eliminado = SimpleNamespace(**_solicitud(solicitud_id=1).__dict__, deleted=1)
    actual = _solicitud(solicitud_id=None)

    assert detectar_duplicado(actual, [eliminado]).hay_duplicado is False
