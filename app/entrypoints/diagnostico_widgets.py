from __future__ import annotations

from collections.abc import Iterable


_CLASES_SPLASH_EXCLUIDAS = {"QSplashScreen", "SplashWindow"}
_CLASES_FALLBACK_EXCLUIDAS = {"FallbackWindow", "RecuperacionArranqueDialog"}
_NOMBRES_EXCLUIDOS = {"startup_fallback_window", "fallback_window", "splash"}


def construir_info_top_level_widgets(widgets: Iterable[object]) -> list[dict[str, object]]:
    """Construye un payload serializable para logging de ventanas top-level."""
    salida: list[dict[str, object]] = []
    for widget in widgets:
        clase = widget.__class__.__name__
        salida.append(
            {
                "clase": clase,
                "object_name": _invocar_o_none(widget, "objectName"),
                "window_title": _invocar_o_none(widget, "windowTitle"),
                "is_visible": bool(_invocar_o_none(widget, "isVisible") or False),
                "is_hidden": bool(_invocar_o_none(widget, "isHidden") or False),
                "is_window": bool(_invocar_o_none(widget, "isWindow") or False),
            }
        )
    return salida


def hay_ventana_visible(toplevel_info: list[dict[str, object]]) -> bool:
    return any(bool(item.get("is_visible")) for item in toplevel_info)


def hay_ventana_visible_no_splash(info_widgets: list[dict[str, object]]) -> bool:
    for item in info_widgets:
        normalizado = _normalizar_info_widget(item)
        if not bool(normalizado.get("is_visible")):
            continue
        clase = str(normalizado.get("clase") or "")
        object_name = str(normalizado.get("object_name") or "").lower()
        if clase in _CLASES_SPLASH_EXCLUIDAS:
            continue
        if clase in _CLASES_FALLBACK_EXCLUIDAS:
            continue
        if object_name in _NOMBRES_EXCLUIDOS:
            continue
        if "fallback" in object_name:
            continue
        return True
    return False


def debe_abortar_watchdog_por_ventana_visible(
    hay_visible_no_splash: bool,
) -> bool:
    return hay_visible_no_splash


def validar_ventana_creada(ventana: object | None) -> None:
    if ventana is None:
        raise RuntimeError("VENTANA_ARRANQUE_NO_CREADA")


def decidir_cerrar_splash(al_mostrar_fallback: bool) -> bool:
    return al_mostrar_fallback


def seleccionar_ventana_principal(
    info_widgets: list[dict[str, object]],
) -> dict[str, object] | None:
    candidatos: list[tuple[int, dict[str, object], str]] = []
    for item in info_widgets:
        normalizado = _normalizar_info_widget(item)
        score, motivo = _calcular_score_ventana(normalizado)
        if score <= 0:
            continue
        candidatos.append((score, item, motivo))
    if not candidatos:
        return None
    candidatos.sort(
        key=lambda valor: (
            valor[0],
            str(_normalizar_info_widget(valor[1]).get("window_title", "")),
            str(_normalizar_info_widget(valor[1]).get("object_name", "")),
        ),
        reverse=True,
    )
    score, elegido, motivo = candidatos[0]
    return {
        "candidato": elegido,
        "motivo": motivo,
        "score": score,
    }


def _calcular_score_ventana(info_widget: dict[str, object]) -> tuple[int, str]:
    clase = str(info_widget.get("clase") or "")
    object_name = str(info_widget.get("object_name") or "").lower()
    window_title = str(info_widget.get("window_title") or "").lower()
    is_visible = bool(info_widget.get("is_visible"))
    is_window = bool(info_widget.get("is_window"))
    if clase in _CLASES_SPLASH_EXCLUIDAS:
        return 0, "splash_excluido"
    if object_name in _NOMBRES_EXCLUIDOS:
        return 0, "fallback_excluido"
    if "fallback" in object_name:
        return 0, "fallback_excluido"
    es_main_window = clase == "QMainWindow"
    es_dialogo = clase in {"QDialog", "QWizard", "WelcomeWizard"} or "wizard" in clase.lower()
    onboarding_en_titulo = "onboarding" in window_title or "bienvenida" in window_title
    if es_main_window and is_visible:
        return 100, "main_window_visible"
    if es_dialogo and is_visible and (bool(info_widget.get("modal")) or onboarding_en_titulo):
        return 90, "wizard_visible"
    if es_dialogo and is_visible:
        return 80, "dialog_visible"
    if es_main_window and is_window:
        return 70, "main_window_no_visible"
    return 0, "descartado"


def _normalizar_info_widget(item: dict[str, object]) -> dict[str, object]:
    return {
        "clase": item.get("clase") or item.get("cls") or "",
        "is_visible": item.get("is_visible")
        if "is_visible" in item
        else item.get("isVisible", False),
        "is_hidden": item.get("is_hidden")
        if "is_hidden" in item
        else item.get("isHidden", False),
        "is_window": item.get("is_window")
        if "is_window" in item
        else item.get("isWindow", False),
        "window_title": item.get("window_title") or item.get("title") or "",
        "object_name": item.get("object_name") or item.get("objectName") or "",
        "modal": item.get("modal", False),
    }


def _invocar_o_none(widget: object, nombre_metodo: str):
    metodo = getattr(widget, nombre_metodo, None)
    if not callable(metodo):
        return None
    try:
        return metodo()
    except Exception:  # noqa: BLE001
        return None
