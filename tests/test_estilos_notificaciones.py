from __future__ import annotations

import ast
from pathlib import Path

from app.ui.estilos.cargador_estilos_notificaciones import (
    construir_estilo_dialogo_confirmacion_resumen,
    construir_estilo_dialogo_operacion_feedback,
    construir_estilo_tarjeta_toast,
)


RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS_UI_SIN_QSS_INLINE = (
    RAIZ / "app" / "ui" / "notification_service.py",
    RAIZ / "app" / "ui" / "widgets" / "widget_toast.py",
)


def test_cargador_estilos_toast_compone_qss_desde_plantilla() -> None:
    estilo = construir_estilo_tarjeta_toast(
        color_texto="#111111",
        color_acento="#222222",
        color_acento_suave="#333333",
        color_fondo="#444444",
        color_cerrar_hover="#555555",
        color_cerrar_pressed="#666666",
    )

    assert "QFrame#toastWidget" in estilo
    assert "#111111" in estilo
    assert "#222222" in estilo
    assert "#333333" in estilo
    assert "#444444" in estilo
    assert "#555555" in estilo
    assert "#666666" in estilo


def test_cargador_estilos_dialogos_compone_qss_desde_plantillas() -> None:
    estilo_operacion = construir_estilo_dialogo_operacion_feedback()
    estilo_confirmacion = construir_estilo_dialogo_confirmacion_resumen(color_borde="#2a9d8f")

    assert "QDialog#dialogoOperacionFeedback" in estilo_operacion
    assert "QDialog#dialogoConfirmacionResumen" in estilo_confirmacion
    assert "#2a9d8f" in estilo_confirmacion


def test_regresion_sin_bloques_qss_inline_en_archivos_ui_problematicos() -> None:
    for archivo in ARCHIVOS_UI_SIN_QSS_INLINE:
        modulo = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(modulo):
            if not isinstance(nodo, ast.Constant) or not isinstance(nodo.value, str):
                continue
            literal = nodo.value.strip()
            assert not (
                any(token in literal for token in ("QDialog#", "QFrame#", "QLabel#", "QPushButton#"))
                or ("{" in literal and "}" in literal and ";" in literal)
            ), f"Se detectó posible QSS inline en {archivo}: {literal[:80]}"
