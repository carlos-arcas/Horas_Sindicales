from __future__ import annotations
from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    CrearPendienteCasoUso,
    SolicitudCrearPendientePeticion,
)


class RepositorioFake:
    def __init__(self) -> None:
        self._pendientes: list[SolicitudDTO] = []

    def crear_pendiente(self, solicitud: SolicitudDTO, correlation_id: str | None = None) -> SolicitudDTO:
        _ = correlation_id
        creada = replace(solicitud, id=101)
        self._pendientes.append(creada)
        return creada

    def listar_pendientes(self) -> list[SolicitudDTO]:
        return list(self._pendientes)


def _solicitud() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=7,
        fecha_solicitud="2026-02-01",
        fecha_pedida="2026-02-15",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas="nota",
    )


def test_crear_pendiente_devuelve_snapshot_y_pendientes_ids() -> None:
    repo = RepositorioFake()
    caso_uso = CrearPendienteCasoUso(repositorio=repo)

    resultado = caso_uso.execute(SolicitudCrearPendientePeticion(solicitud=_solicitud(), correlation_id="corr-test"))

    assert resultado.errores == []
    assert resultado.solicitud_id == 101
    assert resultado.solicitud_creada is not None
    assert resultado.solicitud_creada.id == 101
    assert resultado.pendientes_ids == [101]
    assert resultado.requiere_refresh is True
