from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ui.vistas.main_window import acciones_personas


pytestmark = pytest.mark.headless_safe


class _ComboStub:
    def __init__(self, valores: list[int | None], actual: int | None) -> None:
        self._valores = list(valores)
        self._actual = actual
        self._blocked: list[bool] = []

    def currentData(self) -> int | None:
        return self._actual

    def count(self) -> int:
        return len(self._valores)

    def itemData(self, index: int) -> int | None:
        return self._valores[index]

    def setCurrentIndex(self, index: int) -> None:
        self._actual = self._valores[index]

    def blockSignals(self, value: bool) -> None:
        self._blocked.append(value)


def test_on_persona_changed_sincroniza_contexto_y_refresca_estado_derivado() -> None:
    persona_a = SimpleNamespace(id=1, nombre="Ana")
    persona_b = SimpleNamespace(id=2, nombre="Bea")
    settings = Mock()
    persona_combo = _ComboStub([1, 2], 2)
    config_combo = _ComboStub([1, 2], 1)
    historico_combo = _ComboStub([None, 1, 2], 1)
    pendientes_table = SimpleNamespace(clearSelection=Mock())
    huerfanas_table = SimpleNamespace(clearSelection=Mock())
    window = SimpleNamespace(
        _last_persona_id=1,
        persona_combo=persona_combo,
        config_delegada_combo=config_combo,
        historico_delegada_combo=historico_combo,
        _settings=settings,
        _personas=[persona_a, persona_b],
        pendientes_table=pendientes_table,
        huerfanas_table=huerfanas_table,
        _limpiar_formulario=Mock(),
        _reload_pending_views=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _refrescar_estado_operativa=Mock(),
        _update_global_context=Mock(),
        notas_input=SimpleNamespace(toPlainText=lambda: ""),
        fecha_input=SimpleNamespace(date=lambda: "fecha"),
        desde_input=SimpleNamespace(time=lambda: "desde"),
        hasta_input=SimpleNamespace(time=lambda: "hasta"),
        completo_check=SimpleNamespace(isChecked=lambda: False),
        _draft_solicitud_por_persona={},
    )

    is_form_dirty_original = acciones_personas.is_form_dirty
    try:
        acciones_personas.is_form_dirty = lambda *_args, **_kwargs: False
        acciones_personas.on_persona_changed(window)
    finally:
        acciones_personas.is_form_dirty = is_form_dirty_original

    assert window._last_persona_id == 2
    assert config_combo.currentData() == 2
    assert historico_combo.currentData() == 2
    pendientes_table.clearSelection.assert_called_once()
    huerfanas_table.clearSelection.assert_called_once()
    window._reload_pending_views.assert_called_once()
    window._refresh_historico.assert_called_once()
    window._refresh_saldos.assert_called_once()
    window._refrescar_estado_operativa.assert_called_once_with("persona_changed")
    window._update_global_context.assert_called_once()
    assert settings.setValue.call_args_list[:2] == [
        (("contexto/delegada_activa", 2),),
        (("contexto/delegada_seleccionada_id", 2),),
    ]


def test_on_persona_changed_cancelado_restaura_combo_y_no_refresca() -> None:
    persona_combo = _ComboStub([1, 2], 2)
    window = SimpleNamespace(
        _last_persona_id=1,
        persona_combo=persona_combo,
        config_delegada_combo=_ComboStub([1, 2], 1),
        historico_delegada_combo=_ComboStub([None, 1, 2], 1),
        notas_input=SimpleNamespace(toPlainText=lambda: "borrador"),
        fecha_input=SimpleNamespace(date=lambda: "otra"),
        desde_input=SimpleNamespace(time=lambda: "desde"),
        hasta_input=SimpleNamespace(time=lambda: "hasta"),
        completo_check=SimpleNamespace(isChecked=lambda: False),
        pendientes_table=SimpleNamespace(clearSelection=Mock()),
        huerfanas_table=SimpleNamespace(clearSelection=Mock()),
        _reload_pending_views=Mock(),
        _refresh_historico=Mock(),
        _refresh_saldos=Mock(),
        _refrescar_estado_operativa=Mock(),
        _update_global_context=Mock(),
    )

    confirmar_original = acciones_personas.confirmar_cambio_delegada
    is_form_dirty_original = acciones_personas.is_form_dirty
    try:
        acciones_personas.confirmar_cambio_delegada = lambda *_args, **_kwargs: False
        acciones_personas.is_form_dirty = lambda *_args, **_kwargs: True
        acciones_personas.on_persona_changed(window)
    finally:
        acciones_personas.confirmar_cambio_delegada = confirmar_original
        acciones_personas.is_form_dirty = is_form_dirty_original

    assert persona_combo.currentData() == 1
    window._reload_pending_views.assert_not_called()
    window._refresh_historico.assert_not_called()
    window._refresh_saldos.assert_not_called()
