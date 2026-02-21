from __future__ import annotations

from dataclasses import dataclass

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.application.operaciones.contratos import OperacionConPlan
from app.application.operaciones.modelos import (
    ConflictosOperacion,
    PlanOperacion,
    ResultadoOperacion,
    RutasOperacion,
)


@dataclass(frozen=True)
class RequestOperacionAuditoria:
    dry_run: bool = True
    id_auditoria: str | None = None


class OperacionAuditoriaE2E(OperacionConPlan[RequestOperacionAuditoria]):
    def __init__(self, auditor: AuditarE2E) -> None:
        self._auditor = auditor

    def obtener_plan(self, request: RequestOperacionAuditoria) -> PlanOperacion:
        plan = self._auditor.obtener_plan(RequestAuditoriaE2E(dry_run=request.dry_run, id_auditoria=request.id_auditoria))
        return PlanOperacion(
            operacion="auditoria_e2e",
            dry_run=plan.dry_run,
            descripcion="Auditoría E2E de calidad y arquitectura",
            directorios_previstos=[],
            artefactos_previstos=[],
            metadatos={
                "id_auditoria": plan.id_auditoria,
                "fecha_utc": plan.fecha_utc.isoformat(),
                "checks_objetivo": plan.checks_objetivo,
            },
        )

    def obtener_rutas(self, plan: PlanOperacion) -> RutasOperacion:
        id_auditoria = str(plan.metadatos["id_auditoria"])
        interno = self._auditor.obtener_rutas(
            self._auditor.obtener_plan(RequestAuditoriaE2E(dry_run=plan.dry_run, id_auditoria=id_auditoria))
        )
        return RutasOperacion(
            base_dir=interno.base_dir,
            archivos=[interno.informe_md, interno.informe_json, interno.manifest_json, interno.status_txt],
            directorios=[interno.base_dir],
        )

    def validar_conflictos(self, plan: PlanOperacion) -> ConflictosOperacion:
        id_auditoria = str(plan.metadatos["id_auditoria"])
        conflictos = self._auditor.validar_conflictos(
            self._auditor.obtener_plan(RequestAuditoriaE2E(dry_run=plan.dry_run, id_auditoria=id_auditoria))
        )
        return ConflictosOperacion(conflictos=conflictos.conflictos, no_ejecutable=False)

    def ejecutar(self, request: RequestOperacionAuditoria) -> ResultadoOperacion:
        resultado = self._auditor.ejecutar(RequestAuditoriaE2E(dry_run=request.dry_run, id_auditoria=request.id_auditoria))
        plan = self.obtener_plan(request)
        rutas = self.obtener_rutas(plan)
        conflictos = ConflictosOperacion(conflictos=resultado.conflictos, no_ejecutable=False)
        return ResultadoOperacion(
            operacion="auditoria_e2e",
            dry_run=request.dry_run,
            plan=plan,
            rutas=rutas,
            conflictos=conflictos,
            artefactos_generados=resultado.artefactos_generados,
            mensaje=resultado.resultado_global,
            detalles={"score": resultado.score, "exit_code": resultado.exit_code},
        )
