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
from app.domain.models import Persona


@dataclass(frozen=True)
class RequestExportacionPdfHistorico:
    solicitudes: list[SolicitudDTO]
    persona: Persona | None
    destino: Path
    dry_run: bool = True
    overwrite: bool = False
    intro_text: str | None = None
    logo_path: str | None = None


class ExportacionPdfHistoricoOperacion(OperacionConPlan[RequestExportacionPdfHistorico]):
    def __init__(self, fs: SistemaArchivosPuerto, generador_pdf: GeneradorPdfPuerto | None) -> None:
        self._fs = fs
        self._generador_pdf = generador_pdf

    def obtener_plan(self, request: RequestExportacionPdfHistorico) -> PlanOperacion:
        return PlanOperacion(
            operacion="exportacion_pdf_historico",
            dry_run=request.dry_run,
            descripcion="Exportación de histórico en PDF",
            artefactos_previstos=[str(request.destino)],
            directorios_previstos=[str(request.destino.parent)],
            metadatos={
                "persona_id": request.persona.id if request.persona else None,
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

        if plan.metadatos.get("persona_id") is None:
            conflictos.append("Entrada inválida: persona no encontrada.")
            no_ejecutable = True
        if int(plan.metadatos.get("solicitudes", 0)) <= 0:
            conflictos.append("Entrada inválida: no hay solicitudes para exportar.")
            no_ejecutable = True
        if self._generador_pdf is None:
            conflictos.append("No ejecutable: generador PDF no configurado.")
            no_ejecutable = True

        if self._fs.existe(destino) and not bool(plan.metadatos.get("overwrite")):
            conflictos.append(f"Colisión de ruta destino: {destino}")
            no_ejecutable = True

        return ConflictosOperacion(conflictos=conflictos, no_ejecutable=no_ejecutable)

    def ejecutar(self, request: RequestExportacionPdfHistorico) -> ResultadoOperacion:
        plan = self.obtener_plan(request)
        rutas = self.obtener_rutas(plan)
        conflictos = self.validar_conflictos(plan)

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

        assert self._generador_pdf is not None
        assert request.persona is not None
        self._generador_pdf.generar_pdf_historico(
            request.solicitudes,
            request.persona,
            Path(rutas.archivos[0]),
            intro_text=request.intro_text,
            logo_path=request.logo_path,
        )

        return ResultadoOperacion(
            operacion=plan.operacion,
            dry_run=False,
            plan=plan,
            rutas=rutas,
            conflictos=conflictos,
            artefactos_generados=rutas.archivos,
            mensaje="OK",
        )
