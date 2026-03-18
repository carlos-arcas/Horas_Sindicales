from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_CONTROLLER_PATH = (
    PROJECT_ROOT / "app" / "ui" / "vistas" / "main_window" / "state_controller.py"
)
STATE_HELPERS_PATH = (
    PROJECT_ROOT / "app" / "ui" / "vistas" / "main_window" / "state_helpers.py"
)
UI_MAIN_PATH = PROJECT_ROOT / "app" / "entrypoints" / "ui_main.py"

ARCHIVOS_UI_AUDITADOS = {
    "app/ui/vistas/main_window/state_controller.py",
    "app/ui/vistas/main_window/state_helpers.py",
    "app/entrypoints/ui_main.py",
}

ATRIBUTOS_MUTANTES_AUDITADOS = {
    "agregar_button",
    "insertar_sin_pdf_button",
    "confirmar_button",
    "eliminar_pendiente_button",
    "eliminar_huerfana_button",
    "add_persona_button",
    "edit_persona_button",
    "delete_persona_button",
    "edit_grupo_button",
    "editar_pdf_button",
    "opciones_button",
    "config_sync_button",
    "sync_button",
    "confirm_sync_button",
    "retry_failed_button",
    "accion_menu_cargar_demo",
    "eliminar_button",
    "generar_pdf_button",
}


def _leer(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mainwindow_exige_proveedor_ui_solo_lectura_sin_fallbacks_implicitos() -> None:
    contenido = _leer(STATE_CONTROLLER_PATH)

    assert "ui.read_only.error_proveedor_obligatorio" in contenido
    assert "_resolver_proveedor_ui_solo_lectura_desde_dependencias" not in contenido
    assert "lambda: False" not in contenido
    assert "_politica_modo_solo_lectura" not in contenido


def test_ui_main_inyecta_y_expone_accion_menu_demo_para_fuente_unica() -> None:
    contenido = _leer(UI_MAIN_PATH)

    assert (
        "proveedor_ui_solo_lectura=resolved_container.proveedor_ui_solo_lectura"
        in contenido
    )
    assert "main_window.accion_menu_cargar_demo = accion_cargar_demo" in contenido
    assert "update_actions()" in contenido


def test_inventario_centralizado_de_acciones_mutantes_se_mantiene_estable() -> None:
    modulo = ast.parse(_leer(STATE_HELPERS_PATH), filename=str(STATE_HELPERS_PATH))

    for nodo in modulo.body:
        if (
            isinstance(nodo, ast.AnnAssign)
            and getattr(nodo.target, "id", None) == "ACCIONES_MUTANTES_AUDITADAS_UI"
        ):
            inventario = ast.literal_eval(nodo.value)
            break
    else:  # pragma: no cover - guardarraíl duro
        raise AssertionError("No se encontró ACCIONES_MUTANTES_AUDITADAS_UI")

    assert set(inventario) == ATRIBUTOS_MUTANTES_AUDITADOS


def test_guardarrail_repo_wide_ui_read_only_se_mantiene_acotado() -> None:
    assert ARCHIVOS_UI_AUDITADOS == {
        "app/ui/vistas/main_window/state_controller.py",
        "app/ui/vistas/main_window/state_helpers.py",
        "app/entrypoints/ui_main.py",
    }
