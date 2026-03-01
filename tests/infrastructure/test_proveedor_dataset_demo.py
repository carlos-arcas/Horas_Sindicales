from __future__ import annotations

from app.infrastructure.proveedor_dataset_demo import ProveedorDatasetDemo


def test_proveedor_dataset_demo_entrega_estructura_valida() -> None:
    dataset = ProveedorDatasetDemo().cargar()

    delegadas = dataset.get("delegadas")
    solicitudes = dataset.get("solicitudes")
    assert isinstance(delegadas, list)
    assert isinstance(solicitudes, list)
    assert len(delegadas) >= 2
    assert len(solicitudes) >= 6
    assert all("nombre" in delegada for delegada in delegadas)
