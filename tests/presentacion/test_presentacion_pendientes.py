from __future__ import annotations

from dataclasses import dataclass

from app.ui.vistas.presentacion_pendientes import construir_estado_vista_pendientes


@dataclass(slots=True)
class _EstadoDatasetDummy:
    pendientes_ocultas: list[object]
    pendientes_otras_delegadas: list[object]


def test_ver_todas_delegadas_no_oculta_pendientes_ni_muestra_warning() -> None:
    estado = _EstadoDatasetDummy(
        pendientes_ocultas=[],
        pendientes_otras_delegadas=[],
    )

    vista = construir_estado_vista_pendientes(
        estado_dataset=estado,
        ver_todas_delegadas=True,
    )

    assert vista.warning_visible is False
    assert vista.warning_text == ""
    assert vista.revisar_visible is False


def test_contadores_y_warning_no_se_contradicen_con_filtro_por_delegada() -> None:
    estado = _EstadoDatasetDummy(
        pendientes_ocultas=[object(), object()],
        pendientes_otras_delegadas=[object(), object()],
    )

    vista = construir_estado_vista_pendientes(
        estado_dataset=estado,
        ver_todas_delegadas=False,
    )

    assert vista.warning_visible is True
    assert vista.revisar_visible is True
    assert "2" in vista.warning_text
    assert "2" in vista.revisar_text
