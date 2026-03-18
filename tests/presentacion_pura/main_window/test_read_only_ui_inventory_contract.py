from __future__ import annotations

from pathlib import Path

import pytest

from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    DescriptorAccionMutante,
)
from tests.presentacion_pura.main_window.contrato_inventario_solo_lectura import (
    CAMPOS_RUNTIME_DESCRIPTORES,
    FRAGMENTOS_PROHIBIDOS_EN_RUNTIME,
    validar_contrato_inventario_con_fuentes,
    validar_inventario_runtime_mutante,
)

pytestmark = pytest.mark.headless_safe

PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLITICA_PATH = (
    PROJECT_ROOT / "app" / "ui" / "vistas" / "main_window" / "politica_solo_lectura.py"
)

ACCIONES_CRITICAS = {
    "agregar_button",
    "confirmar_button",
    "sync_button",
    "confirm_sync_button",
    "accion_menu_cargar_demo",
    "eliminar_button",
    "generar_pdf_button",
}


def test_contrato_inventario_apunta_a_controles_reales_de_codigo() -> None:
    assert validar_contrato_inventario_con_fuentes() == []


def test_inventario_no_tiene_duplicados_ni_descriptores_incompletos() -> None:
    assert validar_inventario_runtime_mutante() == []


def test_acciones_criticas_siguen_inventariadas() -> None:
    nombres = {
        descriptor.nombre_control for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    }
    faltantes = ACCIONES_CRITICAS - nombres
    assert not faltantes


def test_descriptor_action_queda_restringido_a_menu_demo() -> None:
    descriptores_action = [
        descriptor
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
        if descriptor.tipo_control == "action"
    ]
    assert descriptores_action == [
        DescriptorAccionMutante(
            "accion_menu_cargar_demo",
            "action",
            "menu_ayuda",
            "cargar_datos_demo",
        )
    ]


def test_guardarrail_no_hay_inventarios_read_only_duplicados_en_otros_modulos() -> None:
    violaciones: list[str] = []
    for path in PROJECT_ROOT.joinpath("app").rglob("*.py"):
        relativo = path.relative_to(PROJECT_ROOT).as_posix()
        if relativo == "app/ui/vistas/main_window/politica_solo_lectura.py":
            continue
        contenido = path.read_text(encoding="utf-8")
        if "DescriptorAccionMutante(" in contenido:
            violaciones.append(relativo)
        if "ACCIONES_MUTANTES_AUDITADAS_UI" in contenido:
            violaciones.append(relativo)
    assert not violaciones


def test_guardarrail_runtime_queda_limitado_a_campos_de_produccion() -> None:
    contenido = POLITICA_PATH.read_text(encoding="utf-8")
    for fragmento in CAMPOS_RUNTIME_DESCRIPTORES:
        assert f"{fragmento}:" in contenido
    for fragmento in FRAGMENTOS_PROHIBIDOS_EN_RUNTIME:
        assert fragmento not in contenido
