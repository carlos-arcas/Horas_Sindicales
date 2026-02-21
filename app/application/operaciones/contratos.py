from __future__ import annotations

from typing import Protocol, TypeVar

from app.application.operaciones.modelos import (
    ConflictosOperacion,
    PlanOperacion,
    ResultadoOperacion,
    RutasOperacion,
)

RequestT = TypeVar("RequestT")


class OperacionConPlan(Protocol[RequestT]):
    def obtener_plan(self, request: RequestT) -> PlanOperacion: ...

    def obtener_rutas(self, plan: PlanOperacion) -> RutasOperacion: ...

    def validar_conflictos(self, plan: PlanOperacion) -> ConflictosOperacion: ...

    def ejecutar(self, request: RequestT) -> ResultadoOperacion: ...
