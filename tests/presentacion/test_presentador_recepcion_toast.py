from __future__ import annotations

from app.ui.toasts.presentador_recepcion_toast import construir_decision_recepcion_toast


def test_decision_recepcion_toast_detecta_ids_eliminados() -> None:
    decision = construir_decision_recepcion_toast(previo_ids=["a", "b", "c"], actuales_ids=["b", "d"])

    assert decision.ids_a_cerrar == ["a", "c"]


def test_decision_recepcion_toast_sin_eliminados_retorna_lista_vacia() -> None:
    decision = construir_decision_recepcion_toast(previo_ids=["a", "b"], actuales_ids=["a", "b", "c"])

    assert decision.ids_a_cerrar == []
