from __future__ import annotations

import logging

from app.ui.copy_catalog import copy_text

logger = logging.getLogger(__name__)


def _resolver_i18n(i18n: object | None, clave: str, fallback: str = "") -> str:
    if i18n is not None and hasattr(i18n, "t"):
        try:
            valor = i18n.t(clave)
            if isinstance(valor, str) and valor.strip():
                return valor
        except Exception:
            logger.warning(
                "UI_I18N_RESOLUTION_FAILED",
                extra={"evento": "resolver_i18n", "clave": clave},
            )
    try:
        return copy_text(clave)
    except Exception:
        return fallback


def configurar_placeholders_hora(window: object, i18n: object | None = None) -> None:
    placeholder = _resolver_i18n(i18n, "ui.solicitudes.formato_hora")
    for nombre in ("desde_input", "hasta_input"):
        widget = getattr(window, nombre, None)
        if widget is None:
            logger.warning(
                "UI_POST_BUILD_WIDGET_MISSING",
                extra={"evento": "configurar_placeholders_hora", "widget": nombre},
            )
            continue
        setter = getattr(widget, "setPlaceholderText", None)
        if callable(setter):
            setter(placeholder)
            continue
        logger.warning(
            "UI_POST_BUILD_PLACEHOLDER_UNSUPPORTED",
            extra={"evento": "configurar_placeholders_hora", "widget": nombre},
        )


def actualizar_columnas_responsivas(window: object) -> None:
    for nombre in ("pending_table", "historico_table"):
        tabla = getattr(window, nombre, None)
        if tabla is None:
            logger.warning(
                "UI_POST_BUILD_WIDGET_MISSING",
                extra={"evento": "actualizar_columnas_responsivas", "widget": nombre},
            )
            continue
        header = getattr(tabla, "horizontalHeader", lambda: None)()
        if header is None:
            logger.warning(
                "UI_POST_BUILD_HEADER_MISSING",
                extra={"evento": "actualizar_columnas_responsivas", "widget": nombre},
            )
            continue
        set_stretch = getattr(header, "setStretchLastSection", None)
        if callable(set_stretch):
            set_stretch(True)


def normalizar_alturas_inputs(window: object) -> None:
    for nombre in ("fecha_input", "desde_input", "hasta_input", "persona_combo"):
        widget = getattr(window, nombre, None)
        if widget is None:
            logger.warning(
                "UI_POST_BUILD_WIDGET_MISSING",
                extra={"evento": "normalizar_alturas_inputs", "widget": nombre},
            )
            continue
        height = 32
        size_hint = getattr(widget, "sizeHint", None)
        if callable(size_hint):
            try:
                hint = size_hint()
                if hasattr(hint, "height"):
                    height = max(height, int(hint.height()))
            except Exception:
                logger.warning(
                    "UI_POST_BUILD_SIZE_HINT_FAILED",
                    extra={"evento": "normalizar_alturas_inputs", "widget": nombre},
                )
        setter = getattr(widget, "setMinimumHeight", None)
        if callable(setter):
            setter(height)
            continue
        logger.warning(
            "UI_POST_BUILD_HEIGHT_UNSUPPORTED",
            extra={"evento": "normalizar_alturas_inputs", "widget": nombre},
        )
