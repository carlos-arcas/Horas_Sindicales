from __future__ import annotations

import ast
from types import SimpleNamespace

import pytest

from app.ui.vistas.main_window import acciones_personas, form_handlers
from tests.helpers_main_window_ast import (
    ROOT,
    es_wrapper_super_minimo,
    metodo_existe_en_super_mainwindow,
    resolver_metodo_wrapper,
)

ARCHIVO_ACCIONES_MIXIN = ROOT / "app/ui/vistas/main_window/acciones_mixin.py"


class _CampoFecha:
    def __init__(self, valor: object) -> None:
        self.valor = valor

    def setDate(self, valor: object) -> None:
        self.valor = valor


class _CampoHora:
    def __init__(self, valor: object) -> None:
        self.valor = valor

    def setTime(self, valor: object) -> None:
        self.valor = valor


class _CheckStub:
    def __init__(self, marcado: bool) -> None:
        self.marcado = marcado

    def setChecked(self, valor: bool) -> None:
        self.marcado = valor


class _TextoStub:
    def __init__(self, valor: str) -> None:
        self.valor = valor

    def clear(self) -> None:
        self.valor = ""


class _LabelStub:
    def __init__(self) -> None:
        self.visible = True

    def setVisible(self, valor: bool) -> None:
        self.visible = valor


class _ComboStub:
    def __init__(self, valores: list[int | None], actual: int | None) -> None:
        self._valores = list(valores)
        self._actual = actual

    def currentData(self) -> int | None:
        return self._actual

    def count(self) -> int:
        return len(self._valores)

    def itemData(self, index: int) -> int | None:
        return self._valores[index]

    def setCurrentIndex(self, index: int) -> None:
        self._actual = self._valores[index]

    def blockSignals(self, _value: bool) -> None:
        return None


class _SetStub(set):
    pass


def _build_window_stub() -> SimpleNamespace:
    return SimpleNamespace(
        fecha_input=_CampoFecha("ayer"),
        desde_input=_CampoHora("10:30"),
        hasta_input=_CampoHora("12:00"),
        completo_check=_CheckStub(True),
        notas_input=_TextoStub("borrador"),
        _field_touched=_SetStub({"fecha"}),
        _blocking_errors=_SetStub({"error"}),
        _warnings=_SetStub({"warning"}),
        solicitud_inline_error=_LabelStub(),
        delegada_field_error=_LabelStub(),
        fecha_field_error=_LabelStub(),
        tramo_field_error=_LabelStub(),
        _refrescar_estado_operativa=lambda *_args, **_kwargs: None,
    )


def _resolver_metodo_acciones_mixin(nombre: str) -> ast.FunctionDef:
    tree = ast.parse(ARCHIVO_ACCIONES_MIXIN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AccionesMainWindowMixin":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == nombre:
                    return child
    raise AssertionError(f"No se encontró {nombre} en {ARCHIVO_ACCIONES_MIXIN}")


def test_main_window_limpiar_formulario_wrapper_apunta_a_contrato_super_valido() -> None:
    wrapper = resolver_metodo_wrapper("_limpiar_formulario")

    assert wrapper is not None
    assert es_wrapper_super_minimo(wrapper.nodo, "_limpiar_formulario")
    assert metodo_existe_en_super_mainwindow("_limpiar_formulario")


def test_main_window_wrappers_super_tienen_destino_real_en_la_jerarquia() -> None:
    source = (ROOT / "app/ui/vistas/main_window_vista.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    faltantes: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "MainWindow":
            continue
        for child in node.body:
            if not isinstance(child, ast.FunctionDef) or len(child.body) != 1:
                continue
            stmt = child.body[0]
            call = stmt.value if isinstance(stmt, (ast.Return, ast.Expr)) else None
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
                continue
            super_call = call.func.value
            if not isinstance(super_call, ast.Call):
                continue
            if not isinstance(super_call.func, ast.Name) or super_call.func.id != "super":
                continue
            if not metodo_existe_en_super_mainwindow(child.name):
                faltantes.append(child.name)

    assert not faltantes, f"Wrappers con super() sin destino en la jerarquía: {faltantes}"


def test_acciones_mixin_reintroduce_contrato_canonico_limpiar_formulario() -> None:
    metodo = _resolver_metodo_acciones_mixin("_limpiar_formulario")

    assert len(metodo.body) == 2
    retorno = metodo.body[1]
    assert isinstance(retorno, ast.Return)
    call = retorno.value
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    assert call.func.attr == "limpiar_formulario"
    assert isinstance(call.func.value, ast.Name)
    assert call.func.value.id == "form_handlers"


def test_form_handlers_limpiar_formulario_ejecuta_limpieza_real(monkeypatch: pytest.MonkeyPatch) -> None:
    window = _build_window_stub()
    monkeypatch.setattr(form_handlers, "QDate", SimpleNamespace(currentDate=lambda: "hoy"))
    monkeypatch.setattr(form_handlers, "QTime", lambda hour, minute: f"{hour:02d}:{minute:02d}")

    form_handlers.limpiar_formulario(window)

    assert window.completo_check.marcado is False
    assert window.notas_input.valor == ""
    assert not window._field_touched
    assert not window._blocking_errors
    assert not window._warnings
    assert window.solicitud_inline_error.visible is False
    assert window.delegada_field_error.visible is False
    assert window.fecha_field_error.visible is False
    assert window.tramo_field_error.visible is False


def test_on_persona_changed_invoca_contrato_limpiar_formulario_sin_attribute_error() -> None:
    persona_combo = _ComboStub([1, 2], 2)
    config_combo = _ComboStub([1, 2], 1)
    historico_combo = _ComboStub([None, 1, 2], 1)
    limpiados: list[str] = []
    window = SimpleNamespace(
        _last_persona_id=1,
        persona_combo=persona_combo,
        config_delegada_combo=config_combo,
        historico_delegada_combo=historico_combo,
        notas_input=SimpleNamespace(toPlainText=lambda: ""),
        fecha_input=SimpleNamespace(date=lambda: "fecha"),
        desde_input=SimpleNamespace(time=lambda: "desde"),
        hasta_input=SimpleNamespace(time=lambda: "hasta"),
        completo_check=SimpleNamespace(isChecked=lambda: False),
        _draft_solicitud_por_persona={},
        _limpiar_formulario=lambda: limpiados.append("ok"),
        _reload_pending_views=lambda: None,
        _refresh_historico=lambda: None,
        _refresh_saldos=lambda: None,
        _refrescar_estado_operativa=lambda *_args, **_kwargs: None,
        _update_global_context=lambda: None,
        pendientes_table=SimpleNamespace(clearSelection=lambda: None),
        huerfanas_table=SimpleNamespace(clearSelection=lambda: None),
        _settings=SimpleNamespace(setValue=lambda *_args, **_kwargs: None),
        _sync_controller=None,
    )

    original_is_form_dirty = acciones_personas.is_form_dirty
    original_restore = acciones_personas.restore_draft_for_persona
    try:
        acciones_personas.is_form_dirty = lambda *_args, **_kwargs: False
        acciones_personas.restore_draft_for_persona = lambda *_args, **_kwargs: None
        acciones_personas.on_persona_changed(window)
    except AttributeError as exc:  # pragma: no cover - regresión exacta
        pytest.fail(f"on_persona_changed no debe propagar AttributeError: {exc}")
    finally:
        acciones_personas.is_form_dirty = original_is_form_dirty
        acciones_personas.restore_draft_for_persona = original_restore

    assert limpiados == ["ok"]
