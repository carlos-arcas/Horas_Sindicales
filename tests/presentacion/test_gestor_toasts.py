from __future__ import annotations

from time import monotonic

from app.ui.toasts.modelo_toast import GestorToasts, ToastModelo


def _toast_modelo(*, toast_id: str, dedupe_key: str | None, mensaje: str) -> ToastModelo:
    ahora = monotonic()
    return ToastModelo(
        id=toast_id,
        tipo="error",
        titulo="Error",
        mensaje=mensaje,
        detalles="detalle",
        dedupe_key=dedupe_key,
        created_at_monotonic=ahora,
        updated_at_monotonic=ahora,
    )


def test_dedupe_misma_clave_actualiza_toast_existente() -> None:
    gestor = GestorToasts(max_toasts=3)
    primero = gestor.agregar_toast(_toast_modelo(toast_id="t1", dedupe_key="K:1", mensaje="m1"))
    segundo = gestor.agregar_toast(_toast_modelo(toast_id="t2", dedupe_key="K:1", mensaje="m2"))

    assert len(gestor.listar()) == 1
    assert segundo.id == primero.id
    assert segundo.mensaje == "m2"
    assert segundo.updated_at_monotonic >= primero.updated_at_monotonic


def test_max_toasts_descarta_los_mas_antiguos() -> None:
    gestor = GestorToasts(max_toasts=3)

    for indice in range(5):
        gestor.agregar_toast(_toast_modelo(toast_id=f"t{indice}", dedupe_key=f"K:{indice}", mensaje=f"m{indice}"))

    ids = [toast.id for toast in gestor.listar()]
    assert len(ids) == 3
    assert ids == ["t2", "t3", "t4"]


def test_cerrar_toast_elimina_por_id() -> None:
    gestor = GestorToasts(max_toasts=3)
    gestor.agregar_toast(_toast_modelo(toast_id="t1", dedupe_key="K:1", mensaje="m1"))
    gestor.cerrar_toast("t1")

    assert gestor.listar() == []
