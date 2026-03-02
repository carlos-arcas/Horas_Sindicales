from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tests.ui.conftest import require_qt

require_qt()

from app.ui.copy_catalog import copy_text
from app.ui.vistas import confirmacion_actions


def test_notificar_colision_renombrado_muestra_warning() -> None:
    warning = Mock()
    ventana = SimpleNamespace(toast=SimpleNamespace(warning=warning))

    confirmacion_actions._notificar_colision_renombrado(
        ventana,
        "/tmp/reporte.pdf",
        Path("/tmp/reporte(1).pdf"),
    )

    warning.assert_called_once_with(
        copy_text("ui.solicitudes.pdf_colision_renombrado").format(nombre="reporte(1).pdf"),
        title=copy_text("ui.solicitudes.confirmacion_titulo"),
    )


def test_mostrar_toast_pdf_guardado_expone_accion_abrir_pdf() -> None:
    toast_show = Mock()
    ventana = SimpleNamespace(toast=SimpleNamespace(show=toast_show))

    confirmacion_actions._mostrar_toast_pdf_guardado(ventana, Path("/tmp/final.pdf"))

    kwargs = toast_show.call_args.kwargs
    assert kwargs["action_label"] == copy_text("ui.solicitudes.abrir_pdf")
    assert callable(kwargs["action_callback"])


def test_execute_confirmar_with_pdf_reenvia_error_de_escritura(monkeypatch) -> None:
    show_error = Mock()
    monkeypatch.setattr(confirmacion_actions, "_show_pdf_write_error", show_error)

    ventana = SimpleNamespace(
        _set_processing_state=lambda _flag: None,
        _pending_view_all=False,
        _solicitudes_controller=SimpleNamespace(
            confirmar_lote=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full"))
        ),
    )

    persona = SimpleNamespace(id=1)
    resultado = confirmacion_actions.execute_confirmar_with_pdf(
        ventana,
        persona,
        selected=[],
        pdf_path="/tmp/fallo.pdf",
    )

    assert resultado is None
    show_error.assert_called_once()
