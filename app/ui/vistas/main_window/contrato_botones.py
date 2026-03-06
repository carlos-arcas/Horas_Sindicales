from __future__ import annotations

from dataclasses import dataclass
import logging

from app.ui.copy_catalog import copy_text


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContratoBoton:
    nombre_atributo_boton: str
    nombre_handler: str
    clave_motivo_no_disponible: str | None = None
    critico: bool = True


@dataclass(frozen=True)
class IncidenciaContratoBoton:
    tipo: str
    nombre_atributo_boton: str
    nombre_handler: str
    detalle: str


CONTRATOS_BOTONES_CRITICOS: tuple[ContratoBoton, ...] = (
    ContratoBoton("open_saldos_modal_button", "_on_open_saldos_modal", "ui.saldos.modal_no_disponible"),
    ContratoBoton("add_persona_button", "_on_add_persona", "ui.wiring.boton_no_disponible"),
    ContratoBoton("edit_persona_button", "_on_edit_persona", "ui.wiring.boton_no_disponible"),
    ContratoBoton("edit_grupo_button", "_on_edit_grupo", "ui.wiring.boton_no_disponible"),
    ContratoBoton("opciones_button", "_on_open_opciones", "ui.wiring.boton_no_disponible"),
    ContratoBoton("delete_persona_button", "_on_delete_persona", "ui.wiring.boton_no_disponible"),
    ContratoBoton("agregar_button", "_on_add_pendiente", "ui.wiring.boton_no_disponible"),
    ContratoBoton("eliminar_pendiente_button", "_on_remove_pendiente", "ui.wiring.boton_no_disponible"),
    ContratoBoton("editar_pdf_button", "_on_edit_pdf", "ui.wiring.boton_no_disponible"),
    ContratoBoton("insertar_sin_pdf_button", "_on_insertar_sin_pdf", "ui.wiring.boton_no_disponible"),
    ContratoBoton("confirmar_button", "_on_confirmar", "ui.wiring.boton_no_disponible"),
    ContratoBoton("eliminar_button", "_on_eliminar", "ui.wiring.boton_no_disponible"),
    ContratoBoton("generar_pdf_button", "_on_generar_pdf_historico", "ui.wiring.boton_no_disponible"),
    ContratoBoton("sync_button", "_on_sync", "ui.wiring.boton_no_disponible"),
    ContratoBoton("confirm_sync_button", "_on_confirm_sync", "ui.wiring.boton_no_disponible"),
    ContratoBoton("simulate_sync_button", "_on_simulate_sync", "ui.wiring.boton_no_disponible"),
    ContratoBoton("retry_failed_button", "_on_retry_failed", "ui.wiring.boton_no_disponible"),
    ContratoBoton("review_conflicts_button", "_on_review_conflicts", "ui.wiring.boton_no_disponible"),
    ContratoBoton("config_sync_button", "_on_sync", "ui.wiring.boton_no_disponible"),
    ContratoBoton("historico_sync_button", "_on_sync", "ui.wiring.boton_no_disponible"),
)


def validar_contrato_botones(
    atributos_disponibles: set[str],
    handlers_disponibles: set[str],
) -> list[IncidenciaContratoBoton]:
    incidencias: list[IncidenciaContratoBoton] = []
    contratos_vistos: set[str] = set()
    for contrato in CONTRATOS_BOTONES_CRITICOS:
        nombre_boton = contrato.nombre_atributo_boton.strip()
        nombre_handler = contrato.nombre_handler.strip()
        if not nombre_boton or not nombre_handler:
            incidencias.append(
                IncidenciaContratoBoton(
                    tipo="contrato_inconsistente",
                    nombre_atributo_boton=contrato.nombre_atributo_boton,
                    nombre_handler=contrato.nombre_handler,
                    detalle="CONTRATO_BOTON_HANDLER_VACIO",
                )
            )
            continue
        if nombre_boton in contratos_vistos:
            incidencias.append(
                IncidenciaContratoBoton(
                    tipo="contrato_inconsistente",
                    nombre_atributo_boton=nombre_boton,
                    nombre_handler=nombre_handler,
                    detalle="CONTRATO_BOTON_DUPLICADO",
                )
            )
            continue
        contratos_vistos.add(nombre_boton)
        if nombre_boton not in atributos_disponibles:
            incidencias.append(
                IncidenciaContratoBoton(
                    tipo="boton_no_existente",
                    nombre_atributo_boton=nombre_boton,
                    nombre_handler=nombre_handler,
                    detalle="BOTON_DECLARADO_NO_EXISTE",
                )
            )
        if nombre_handler not in handlers_disponibles:
            incidencias.append(
                IncidenciaContratoBoton(
                    tipo="handler_no_existente",
                    nombre_atributo_boton=nombre_boton,
                    nombre_handler=nombre_handler,
                    detalle="HANDLER_DECLARADO_NO_EXISTE",
                )
            )
    return incidencias


def aplicar_contrato_botones_criticos_runtime(window: object) -> list[IncidenciaContratoBoton]:
    atributos_disponibles = set(dir(window))
    handlers_disponibles = {
        nombre for nombre in atributos_disponibles if callable(getattr(window, nombre, None))
    }
    incidencias = validar_contrato_botones(atributos_disponibles, handlers_disponibles)
    for contrato in CONTRATOS_BOTONES_CRITICOS:
        boton = getattr(window, contrato.nombre_atributo_boton, None)
        if boton is None:
            continue
        disponible, motivo = _resolver_disponibilidad(window, contrato)
        if disponible:
            continue
        if hasattr(boton, "setEnabled"):
            boton.setEnabled(False)
        if hasattr(boton, "setToolTip"):
            boton.setToolTip(copy_text(motivo))
        logger.warning(
            "UI_BUTTON_HANDLER_UNAVAILABLE",
            extra={
                "boton": contrato.nombre_atributo_boton,
                "handler": contrato.nombre_handler,
                "motivo": motivo,
            },
        )
    return incidencias


def _resolver_disponibilidad(window: object, contrato: ContratoBoton) -> tuple[bool, str]:
    handler = getattr(window, contrato.nombre_handler, None)
    if not callable(handler):
        return False, contrato.clave_motivo_no_disponible or "ui.wiring.boton_no_disponible"

    if contrato.nombre_atributo_boton == "open_saldos_modal_button":
        dialogo = getattr(window, "_saldos_dialog_class", None)
        if dialogo is None:
            return False, "ui.saldos.modal_no_disponible"

    return True, ""
