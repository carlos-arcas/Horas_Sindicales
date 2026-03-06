from __future__ import annotations

import logging
from typing import Any

from app.ui.qt.contrato_senales import (
    ADAPTADORES_SENALES,
    CONTRATOS_SENALES_MAIN_WINDOW,
    ContratoSenal,
    IncidenciaContratoSenal,
    validar_contrato_senales,
)
from app.ui.qt.slot_seguro import envolver_slot_seguro


logger = logging.getLogger(__name__)
_ATTR_BINDINGS = "_wiring_contrato_senales_registrados"


def aplicar_contrato_senales_runtime(window: object) -> list[IncidenciaContratoSenal]:
    atributos_disponibles = set(dir(window))
    handlers_disponibles = {
        nombre for nombre in atributos_disponibles if callable(getattr(window, nombre, None))
    }
    incidencias = validar_contrato_senales(
        atributos_disponibles,
        handlers_disponibles,
        set(ADAPTADORES_SENALES),
    )
    for incidencia in incidencias:
        logger.warning(
            "UI_SIGNAL_WIRING_UNAVAILABLE",
            extra={
                "emisor": incidencia.emisor,
                "senal": incidencia.senal,
                "handler": incidencia.handler,
                "motivo": incidencia.motivo,
            },
        )

    incidencias_por_clave = {(item.emisor, item.senal, item.handler) for item in incidencias}
    for contrato in CONTRATOS_SENALES_MAIN_WINDOW:
        clave_contrato = (contrato.emisor, contrato.senal, contrato.handler)
        if clave_contrato in incidencias_por_clave:
            continue
        _conectar_senal_contrato(window, contrato)

    return incidencias


def _conectar_senal_contrato(window: object, contrato: ContratoSenal) -> None:
    emisor = getattr(window, contrato.emisor, None)
    if emisor is None:
        return
    senal = _resolver_senal(emisor, contrato.senal)
    if senal is None:
        logger.warning(
            "UI_SIGNAL_WIRING_UNAVAILABLE",
            extra={
                "emisor": contrato.emisor,
                "senal": contrato.senal,
                "handler": contrato.handler,
                "motivo": "SENAL_NO_EXISTENTE",
            },
        )
        return

    handler = getattr(window, contrato.handler, None)
    if not callable(handler):
        return

    adaptador = ADAPTADORES_SENALES[contrato.adaptador]
    slot_adaptado = adaptador(handler)
    slot_seguro = envolver_slot_seguro(
        slot_adaptado,
        contexto=f"contrato_senales_{contrato.emisor}_{contrato.senal}",
        logger=logger,
        toast=getattr(window, "toast", None),
    )
    key = (id(senal), contrato.handler, contrato.adaptador)
    if _binding_ya_registrado(window, key):
        return
    senal.connect(slot_seguro)


def _resolver_senal(emisor: object, ruta_senal: str) -> Any | None:
    actual: Any = emisor
    for parte in ruta_senal.split("."):
        actual = getattr(actual, parte, None)
        if actual is None:
            return None
        if callable(actual) and parte == "selectionModel":
            actual = actual()
            if actual is None:
                return None
    return actual


def _binding_ya_registrado(window: object, key: tuple[int, str, str]) -> bool:
    registrados = getattr(window, _ATTR_BINDINGS, None)
    if registrados is None:
        registrados = set()
        setattr(window, _ATTR_BINDINGS, registrados)
    if key in registrados:
        return True
    registrados.add(key)
    return False
