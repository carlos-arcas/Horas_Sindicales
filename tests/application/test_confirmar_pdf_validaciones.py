from app.application.use_cases.solicitudes.validaciones import validar_seleccion_confirmacion


def test_confirmar_pdf_sin_seleccion_devuelve_warning() -> None:
    mensaje = validar_seleccion_confirmacion(0)

    assert mensaje is not None
    assert "Selecciona al menos una solicitud pendiente" in mensaje


def test_confirmar_pdf_con_seleccion_no_devuelve_warning() -> None:
    assert validar_seleccion_confirmacion(2) is None
