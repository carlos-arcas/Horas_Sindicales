from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.operaciones.contratos import OperacionConPlan
from app.application.operaciones.modelos import (
    ConflictosOperacion,
    PlanOperacion,
    ResultadoOperacion,
    RutasOperacion,
)
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.core.metrics import medir_tiempo, metrics_registry


@dataclass(frozen=True)
class RequestConfirmacionPdf:
    solicitudes: list[SolicitudDTO]
    destino: Path
    dry_run: bool = True
    overwrite: bool = False


class ConfirmacionPdfOperacion(OperacionConPlan[RequestConfirmacionPdf]):
    def __init__(self, fs: SistemaArchivosPuerto, generador_pdf: GeneradorPdfPuerto | None) -> None:
        self._fs = fs
        self._generador_pdf = generador_pdf

    def obtener_plan(self, request: RequestConfirmacionPdf) -> PlanOperacion:
        return PlanOperacion(
            operacion="confirmacion_pdf_peticiones",
            dry_run=request.dry_run,
            descripcion="Confirmación de peticiones con exportación PDF",
            artefactos_previstos=[str(request.destino)],
            directorios_previstos=[str(request.destino.parent)],
            metadatos={
                "solicitudes": len(request.solicitudes),
                "overwrite": request.overwrite,
            },
        )

    def obtener_rutas(self, plan: PlanOperacion) -> RutasOperacion:
        return RutasOperacion(
            base_dir=plan.directorios_previstos[0] if plan.directorios_previstos else None,
            archivos=plan.artefactos_previstos,
            directorios=plan.directorios_previstos,
        )

    def validar_conflictos(self, plan: PlanOperacion) -> ConflictosOperacion:
        conflictos: list[str] = []
        no_ejecutable = False
        destino = Path(plan.artefactos_previstos[0])

        if int(plan.metadatos.get("solicitudes", 0)) <= 0:
            conflictos.append("Entrada inválida: no hay peticiones para confirmar.")
            no_ejecutable = True
        if destino.suffix.lower() != ".pdf":
            conflictos.append("Ruta inválida: el destino debe tener extensión .pdf.")
            no_ejecutable = True
        if self._generador_pdf is None:
            conflictos.append("No ejecutable: generador PDF no configurado.")
            no_ejecutable = True
        if self._fs.existe(destino) and not bool(plan.metadatos.get("overwrite")):
            conflictos.append(f"Colisión de ruta destino: {destino}")
            no_ejecutable = True

        return ConflictosOperacion(conflictos=conflictos, no_ejecutable=no_ejecutable)

    @medir_tiempo("latency.confirmar_solicitudes_ms")
    def ejecutar(self, request: RequestConfirmacionPdf) -> ResultadoOperacion:
        plan = self.obtener_plan(request)
        rutas = self.obtener_rutas(plan)
        conflictos = self.validar_conflictos(plan)
        if conflictos.conflictos:
            metrics_registry.incrementar("conflictos_detectados", len(conflictos.conflictos))

        if conflictos.no_ejecutable:
            return ResultadoOperacion(
                operacion=plan.operacion,
                dry_run=request.dry_run,
                plan=plan,
                rutas=rutas,
                conflictos=conflictos,
                artefactos_generados=[],
                mensaje="NO_EJECUTABLE",
            )

        if request.dry_run:
            return ResultadoOperacion(
                operacion=plan.operacion,
                dry_run=True,
                plan=plan,
                rutas=rutas,
                conflictos=conflictos,
                artefactos_generados=[],
                mensaje="DRY_RUN",
            )

        for directory in rutas.directorios:
            self._fs.mkdir(Path(directory), parents=True, exist_ok=True)

        return ResultadoOperacion(
            operacion=plan.operacion,
            dry_run=False,
            plan=plan,
            rutas=rutas,
            conflictos=conflictos,
            artefactos_generados=rutas.archivos,
            mensaje="OK",
        )
