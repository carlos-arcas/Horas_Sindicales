import pytest


@pytest.mark.skip(reason="Entorno CI sin librerías gráficas de Qt (libGL.so.1).")
def test_placeholder_main_window_confirmar_pdf() -> None:
    pass
