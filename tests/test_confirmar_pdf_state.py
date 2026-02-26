from app.ui.vistas.confirmar_pdf_state import debe_habilitar_confirmar_pdf


def test_debe_habilitar_confirmar_pdf_con_cero_pendientes() -> None:
    assert debe_habilitar_confirmar_pdf(0) is False


def test_debe_habilitar_confirmar_pdf_con_uno_o_mas_pendientes() -> None:
    assert debe_habilitar_confirmar_pdf(1) is True
    assert debe_habilitar_confirmar_pdf(5) is True
