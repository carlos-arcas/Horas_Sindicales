from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ui.mappers import dto_a_historico_viewmodel, dto_a_pendiente_viewmodel, dto_a_viewmodel


@dataclass
class FakeSolicitudDTO:
    id: int | None = 1
    fecha_pedida: str | date = "2026-01-01"
    horas: float | int | None = 2.5
    observaciones: str | None = "Observación"
    generated: bool = False



def test_mapper_dto_a_viewmodel_mapea_campos_base() -> None:
    dto = FakeSolicitudDTO()

    viewmodel = dto_a_viewmodel(dto)

    assert viewmodel.id == 1
    assert viewmodel.fecha == "2026-01-01"
    assert viewmodel.horas == "2.5"
    assert viewmodel.estado == "PENDIENTE"
    assert viewmodel.descripcion == "Observación"



def test_mapper_dto_a_historico_viewmodel_usa_estado_confirmada() -> None:
    dto = FakeSolicitudDTO(generated=True, horas=3)

    viewmodel = dto_a_historico_viewmodel(dto)

    assert viewmodel.id == 1
    assert viewmodel.fecha == "2026-01-01"
    assert viewmodel.horas == "3"
    assert viewmodel.estado == "CONFIRMADA"



def test_mapper_dto_a_pendiente_viewmodel_tolera_opcionales() -> None:
    dto = FakeSolicitudDTO(id=None, fecha_pedida=date(2026, 2, 5), horas=None, observaciones=None)

    viewmodel = dto_a_pendiente_viewmodel(dto)

    assert viewmodel.id == 0
    assert viewmodel.fecha == "2026-02-05"
    assert viewmodel.horas == "0"
    assert viewmodel.descripcion == ""
