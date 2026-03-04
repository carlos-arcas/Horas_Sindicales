from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import logging
from pathlib import Path
from typing import Protocol

from app.application.dto import SolicitudDTO
from app.application.operaciones.exportacion_pdf_historico_operacion import (
    ExportacionPdfHistoricoOperacion,
    RequestExportacionPdfHistorico,
)
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.core.observability import log_event
from app.domain.models import Persona

logger = logging.getLogger(__name__)


def _artefactos_desde_payload(payload: dict[str, object]) -> list[str]:
    artefactos = payload.get("artefactos_generados")
    if isinstance(artefactos, list):
        return [str(ruta) for ruta in artefactos]
    return []


class RelojPuerto(Protocol):
    def ahora_utc(self) -> datetime: ...


@dataclass(frozen=True)
class EntradaExportacionPeriodo:
    fecha_desde: date
    fecha_hasta: date
    filtro_delegada: int | None = None
    destino: Path | None = None
    dry_run: bool = True
    correlation_id: str = ""


@dataclass(frozen=True)
class PlanExportacion:
    incident_id: str
    correlation_id: str
    carpeta_destino: str
    rutas_previstas: list[str]
    conteo_previsto: int
    warnings: list[str]
    acciones_sugeridas: list[str]
    fecha_desde: str
    fecha_hasta: str
    filtro_delegada: int | None


@dataclass(frozen=True)
class ResultadoExportacion:
    estado: str
    incident_id: str
    correlation_id: str
    carpeta_destino: str
    artefactos_generados: list[str]
    rutas_informe: dict[str, str]
    checks: list[dict[str, str]]


class ExportarCompartirPeriodoCasoUso:
    def __init__(
        self,
        *,
        fs: SistemaArchivosPuerto,
        reloj: RelojPuerto,
        exportador_pdf: GeneradorPdfPuerto,
    ) -> None:
        self._fs = fs
        self._reloj = reloj
        self._exportador_pdf = exportador_pdf

    def crear_plan(
        self,
        entrada: EntradaExportacionPeriodo,
        solicitudes: list[SolicitudDTO],
        persona: Persona | None,
    ) -> PlanExportacion:
        incident_id = self._incident_id()
        correlation_id = entrada.correlation_id or incident_id
        base = entrada.destino or Path("logs/evidencias/export_share")
        carpeta = base / incident_id
        rutas = self._rutas_previstas(carpeta)
        warnings = self._validar_conflictos(entrada, solicitudes, persona, rutas)
        return PlanExportacion(
            incident_id=incident_id,
            correlation_id=correlation_id,
            carpeta_destino=str(carpeta),
            rutas_previstas=rutas,
            conteo_previsto=len(solicitudes),
            warnings=warnings,
            acciones_sugeridas=["abrir_carpeta", "copiar_ruta", "ver_informe"],
            fecha_desde=entrada.fecha_desde.isoformat(),
            fecha_hasta=entrada.fecha_hasta.isoformat(),
            filtro_delegada=entrada.filtro_delegada,
        )

    def ejecutar(
        self,
        plan: PlanExportacion,
        solicitudes: list[SolicitudDTO],
        persona: Persona | None,
    ) -> ResultadoExportacion:
        if persona is None or not solicitudes:
            return ResultadoExportacion(
                estado="FAIL",
                incident_id=plan.incident_id,
                correlation_id=plan.correlation_id,
                carpeta_destino=plan.carpeta_destino,
                artefactos_generados=[],
                rutas_informe={"md": plan.rutas_previstas[2], "json": plan.rutas_previstas[3]},
                checks=[{"check": "precondiciones", "estado": "FAIL"}],
            )
        carpeta = Path(plan.carpeta_destino)
        self._fs.mkdir(carpeta, parents=True, exist_ok=True)
        pdf_destino = Path(plan.rutas_previstas[0])
        op_pdf = ExportacionPdfHistoricoOperacion(fs=self._fs, generador_pdf=self._exportador_pdf)
        resultado_pdf = op_pdf.ejecutar(
            RequestExportacionPdfHistorico(
                solicitudes=solicitudes,
                persona=persona,
                destino=pdf_destino,
                dry_run=False,
                overwrite=True,
            )
        )
        auditoria_json = self._build_auditoria_json(plan, resultado_pdf.artefactos_generados)
        auditoria_md = self._build_auditoria_md(auditoria_json)
        self._fs.escribir_texto(Path(plan.rutas_previstas[1]), json.dumps(auditoria_json, indent=2, ensure_ascii=False))
        self._fs.escribir_texto(Path(plan.rutas_previstas[2]), auditoria_md)
        self._fs.escribir_texto(Path(plan.rutas_previstas[3]), json.dumps(auditoria_json, indent=2, ensure_ascii=False))
        log_event(
            logger,
            "exportar_compartir_periodo_ejecutado",
            {"incident_id": plan.incident_id, "artefactos": resultado_pdf.artefactos_generados},
            plan.correlation_id,
        )
        checks = [
            {"check": "pdf_generado", "estado": "PASS" if resultado_pdf.artefactos_generados else "FAIL"},
            {"check": "auditoria_generada", "estado": "PASS"},
        ]
        estado = "PASS" if all(item["estado"] == "PASS" for item in checks) else "FAIL"
        artefactos = list(resultado_pdf.artefactos_generados) + plan.rutas_previstas[1:4]
        return ResultadoExportacion(
            estado=estado,
            incident_id=plan.incident_id,
            correlation_id=plan.correlation_id,
            carpeta_destino=plan.carpeta_destino,
            artefactos_generados=artefactos,
            rutas_informe={"md": plan.rutas_previstas[2], "json": plan.rutas_previstas[3]},
            checks=checks,
        )

    def _validar_conflictos(
        self,
        entrada: EntradaExportacionPeriodo,
        solicitudes: list[SolicitudDTO],
        persona: Persona | None,
        rutas: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        if entrada.fecha_desde > entrada.fecha_hasta:
            warnings.append("Rango de fechas inválido")
        if persona is None:
            warnings.append("Delegada no encontrada")
        if not solicitudes:
            warnings.append("Sin solicitudes para exportar")
        if any(self._fs.existe(Path(ruta)) for ruta in rutas):
            warnings.append("Existen artefactos previos en destino")
        return warnings

    def _rutas_previstas(self, carpeta: Path) -> list[str]:
        return [
            str(carpeta / "historico.pdf"),
            str(carpeta / "exportacion_auditoria.json"),
            str(carpeta / "exportacion_auditoria.md"),
            str(carpeta / "reporte_reproducible.json"),
        ]

    def _build_auditoria_json(self, plan: PlanExportacion, artefactos_pdf: list[str]) -> dict[str, object]:
        return {
            "incident_id": plan.incident_id,
            "correlation_id": plan.correlation_id,
            "parametros": {
                "fecha_desde": plan.fecha_desde,
                "fecha_hasta": plan.fecha_hasta,
                "filtro_delegada": plan.filtro_delegada,
            },
            "artefactos_generados": artefactos_pdf + plan.rutas_previstas[1:4],
            "checks": [
                {"id": "CHECK-PDF", "estado": "PASS" if artefactos_pdf else "FAIL"},
                {"id": "CHECK-AUDIT", "estado": "PASS"},
            ],
            "estado_global": "PASS" if artefactos_pdf else "FAIL",
        }

    def _build_auditoria_md(self, payload: dict[str, object]) -> str:
        return "\n".join(
            [
                f"# Exportar y Compartir ({payload['incident_id']})",
                f"- Correlation: {payload['correlation_id']}",
                f"- Estado: **{payload['estado_global']}**",
                "",
                "## Artefactos",
                *[f"- {ruta}" for ruta in _artefactos_desde_payload(payload)],
            ]
        )

    def _incident_id(self) -> str:
        ahora = self._reloj.ahora_utc()
        return f"EXP-{ahora.strftime('%Y%m%d-%H%M%S')}"
