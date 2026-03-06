from __future__ import annotations

from app.ui.qt.contrato_senales import (
    ADAPTADORES_SENALES,
    CONTRATOS_SENALES_MAIN_WINDOW,
    adaptar_bool,
    adaptar_selection_changed,
    adaptar_sin_args,
    adaptar_variable,
    validar_contrato_senales,
)


def test_validar_contrato_senales_valido_sin_incidencias() -> None:
    emisores = {contrato.emisor for contrato in CONTRATOS_SENALES_MAIN_WINDOW}
    handlers = {contrato.handler for contrato in CONTRATOS_SENALES_MAIN_WINDOW}
    adaptadores = set(ADAPTADORES_SENALES)

    incidencias = validar_contrato_senales(emisores, handlers, adaptadores)

    assert incidencias == []


def test_validar_contrato_senales_detecta_emisor_faltante() -> None:
    contrato = CONTRATOS_SENALES_MAIN_WINDOW[0]
    emisores = {item.emisor for item in CONTRATOS_SENALES_MAIN_WINDOW if item.emisor != contrato.emisor}
    handlers = {item.handler for item in CONTRATOS_SENALES_MAIN_WINDOW}

    incidencias = validar_contrato_senales(emisores, handlers, set(ADAPTADORES_SENALES))

    assert any(item.motivo == "EMISOR_NO_EXISTENTE" and item.emisor == contrato.emisor for item in incidencias)


def test_validar_contrato_senales_detecta_handler_faltante() -> None:
    contrato = CONTRATOS_SENALES_MAIN_WINDOW[0]
    emisores = {item.emisor for item in CONTRATOS_SENALES_MAIN_WINDOW}
    handlers = {item.handler for item in CONTRATOS_SENALES_MAIN_WINDOW if item.handler != contrato.handler}

    incidencias = validar_contrato_senales(emisores, handlers, set(ADAPTADORES_SENALES))

    assert any(item.motivo == "HANDLER_NO_EXISTENTE" and item.handler == contrato.handler for item in incidencias)


def test_validar_contrato_senales_detecta_adaptador_faltante() -> None:
    contrato = CONTRATOS_SENALES_MAIN_WINDOW[0]
    emisores = {item.emisor for item in CONTRATOS_SENALES_MAIN_WINDOW}
    handlers = {item.handler for item in CONTRATOS_SENALES_MAIN_WINDOW}
    adaptadores = {nombre for nombre in ADAPTADORES_SENALES if nombre != contrato.adaptador}

    incidencias = validar_contrato_senales(emisores, handlers, adaptadores)

    assert any(item.motivo == "ADAPTADOR_NO_EXISTENTE" and item.handler == contrato.handler for item in incidencias)


def test_adaptar_bool_llama_handler_con_bool_robusto() -> None:
    capturado: list[bool] = []

    def handler(valor: bool) -> None:
        capturado.append(valor)

    slot = adaptar_bool(handler)
    slot("sí")

    assert capturado == [True]


def test_adaptar_selection_changed_ignora_payload_extra_sin_type_error() -> None:
    invocado = {"ok": False}

    def handler() -> None:
        invocado["ok"] = True

    slot = adaptar_selection_changed(handler)
    slot("actual", "anterior", "extra")

    assert invocado["ok"] is True


def test_adaptar_variable_no_propaga_error_por_args_adicionales() -> None:
    capturado: list[str] = []

    def handler(valor: str) -> None:
        capturado.append(valor)

    slot = adaptar_variable(handler)
    slot("ok", "extra", "extra2")

    assert capturado == ["ok"]


def test_adaptar_sin_args_llama_con_args_extra() -> None:
    invocaciones = {"total": 0}

    def handler() -> None:
        invocaciones["total"] += 1

    slot = adaptar_sin_args(handler)
    slot(1, 2, 3)

    assert invocaciones["total"] == 1
