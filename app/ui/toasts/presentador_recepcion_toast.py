from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionRecepcionToast:
    ids_a_cerrar: list[str]


def construir_decision_recepcion_toast(*, previo_ids: list[str], actuales_ids: list[str]) -> DecisionRecepcionToast:
    return DecisionRecepcionToast(
        ids_a_cerrar=[toast_id for toast_id in previo_ids if toast_id not in actuales_ids],
    )


__all__ = [DecisionRecepcionToast.__name__, construir_decision_recepcion_toast.__name__]
