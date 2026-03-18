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
POLITICA_SOLO_LECTURA_PATH = (
    PROJECT_ROOT
    / "app"
    / "ui"
    / "vistas"
    / "main_window"
    / "politica_solo_lectura.py"
)
UI_MAIN_PATH = PROJECT_ROOT / "app" / "entrypoints" / "ui_main.py"

ARCHIVOS_UI_AUDITADOS = {
    "app/ui/vistas/main_window/state_controller.py",
    "app/ui/vistas/main_window/state_helpers.py",
    "app/ui/vistas/main_window/politica_solo_lectura.py",
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
    contenido = _leer(POLITICA_SOLO_LECTURA_PATH)
    assert "class DescriptorAccionMutante" in contenido
    assert "ACCIONES_MUTANTES_AUDITADAS_UI: tuple[DescriptorAccionMutante, ...]" in contenido
    modulo = ast.parse(contenido, filename=str(POLITICA_SOLO_LECTURA_PATH))
    nombres = {
        nodo.id
        for nodo in ast.walk(modulo)
        if isinstance(nodo, ast.Name) and nodo.id == "DescriptorAccionMutante"
    }
    assert "DescriptorAccionMutante" in nombres
    assert set(_extraer_nombres_controles_mutantes(modulo)) == ATRIBUTOS_MUTANTES_AUDITADOS


def _extraer_nombres_controles_mutantes(modulo: ast.Module) -> list[str]:
    nombres: list[str] = []
    for nodo in modulo.body:
        if (
            isinstance(nodo, ast.AnnAssign)
            and getattr(nodo.target, "id", None) == "ACCIONES_MUTANTES_AUDITADAS_UI"
            and isinstance(nodo.value, ast.Tuple)
        ):
            for elemento in nodo.value.elts:
                if (
                    isinstance(elemento, ast.Call)
                    and getattr(elemento.func, "id", None)
                    == "DescriptorAccionMutante"
                    and elemento.args
                    and isinstance(elemento.args[0], ast.Constant)
                    and isinstance(elemento.args[0].value, str)
                ):
                    nombres.append(elemento.args[0].value)
            return nombres
    raise AssertionError("No se encontró ACCIONES_MUTANTES_AUDITADAS_UI")


def test_state_helpers_delega_read_only_a_modulo_dedicado() -> None:
    contenido = _leer(STATE_HELPERS_PATH)

    assert "from .politica_solo_lectura import aplicar_politica_solo_lectura" in contenido
    assert "aplicar_politica_solo_lectura(window)" in contenido
    assert "ACCIONES_MUTANTES_AUDITADAS_UI" not in contenido
    assert "tooltip_mutacion_bloqueada" not in contenido
    assert "_aplicar_modo_solo_lectura" not in contenido


def test_guardarrail_no_hay_checks_manuals_read_only_fuera_modulo_dedicado() -> None:
    violaciones: list[str] = []
    for path in PROJECT_ROOT.joinpath("app", "ui").rglob("*.py"):
        relativo = path.relative_to(PROJECT_ROOT).as_posix()
        if relativo in {
            "app/ui/vistas/main_window/politica_solo_lectura.py",
            "app/ui/vistas/main_window/state_controller.py",
        }:
            continue
        contenido = _leer(path)
        if "_proveedor_ui_solo_lectura" in contenido or "tooltip_mutacion_bloqueada" in contenido:
            violaciones.append(relativo)

    assert not violaciones, (
        "La política UI read-only debe vivir centralizada en politica_solo_lectura.py.\n"
        + "\n".join(violaciones)
    )


def test_guardarrail_repo_wide_ui_read_only_se_mantiene_acotado() -> None:
    assert ARCHIVOS_UI_AUDITADOS == {
        "app/ui/vistas/main_window/state_controller.py",
        "app/ui/vistas/main_window/state_helpers.py",
        "app/ui/vistas/main_window/politica_solo_lectura.py",
        "app/entrypoints/ui_main.py",
    }
