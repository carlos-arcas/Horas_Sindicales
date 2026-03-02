from app.ui.models.solicitudes_table_presenter import SolicitudDisplayEntrada, build_display, resumen_nota


def test_resumen_nota_no_expone_texto_completo() -> None:
    nota = "Paciente con dato sensible 12345678A"
    assert resumen_nota(nota) == f"🔒 {len(nota)}"
    assert "sensible" not in resumen_nota(nota)


def test_columna_notas_muestra_indicador_y_no_texto() -> None:
    nota = "Informe clínico con PII"
    entrada = SolicitudDisplayEntrada(
        column=5,
        fecha_pedida="2026-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        notas=nota,
        generated=False,
        show_estado=False,
        show_delegada=False,
    )
    salida = build_display(entrada)
    assert salida.texto_display == f"🔒 {len(nota)}"
    assert nota not in (salida.texto_display or "")
