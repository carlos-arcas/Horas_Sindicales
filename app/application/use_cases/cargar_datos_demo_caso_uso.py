from __future__ import annotations

import logging
from dataclasses import dataclass

from app.application.ports.datos_demo_puerto import CargadorDatosDemoPuerto, ResultadoCargaDemoPuerto

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CargarDatosDemoResultado:
    ok: bool
    mensaje_usuario: str
    detalles: str | None
    warnings: tuple[str, ...]
    acciones_sugeridas: tuple[str, ...]


class CargarDatosDemoCasoUso:
    def __init__(self, cargador: CargadorDatosDemoPuerto) -> None:
        self._cargador = cargador

    def crear_plan(self, modo: str = "BACKUP") -> tuple[str, ...]:
        if modo.upper() == "BACKUP":
            return (
                "validar_dataset_demo",
                "crear_backup_bd_actual",
                "recrear_datos_demo",
                "confirmar_integridad_minima",
            )
        return ("validar_dataset_demo", "recrear_bd_demo_separada", "confirmar_integridad_minima")

    def ejecutar(self, modo: str = "BACKUP") -> CargarDatosDemoResultado:
        plan = self.crear_plan(modo)
        logger.info(
            "carga_demo_iniciada",
            extra={"extra": {"modo": modo, "plan": plan}},
        )
        resultado_puerto = self._cargador.cargar(modo)
        resultado = self._mapear_resultado(resultado_puerto)
        logger.info(
            "carga_demo_finalizada",
            extra={
                "extra": {
                    "modo": modo,
                    "ok": resultado.ok,
                    "acciones": resultado.acciones_sugeridas,
                    "warnings": resultado.warnings,
                }
            },
        )
        return resultado

    def _mapear_resultado(self, resultado: ResultadoCargaDemoPuerto) -> CargarDatosDemoResultado:
        return CargarDatosDemoResultado(
            ok=resultado.ok,
            mensaje_usuario=resultado.mensaje_usuario,
            detalles=resultado.detalles,
            warnings=resultado.warnings,
            acciones_sugeridas=resultado.acciones_sugeridas,
        )
