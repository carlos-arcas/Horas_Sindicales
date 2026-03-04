from app.ui.viewmodels import (
    HistoricoSolicitudViewModel,
    PendienteSolicitudViewModel,
    SolicitudViewModel,
)


def test_viewmodels_creacion() -> None:
    s = SolicitudViewModel(1, "01/01/2026", "2", "CONFIRMADA", "")
    h = HistoricoSolicitudViewModel(1, "01/01/2026", "2", "CONFIRMADA")
    p = PendienteSolicitudViewModel(1, "01/01/2026", "2", "pendiente")

    assert s.id == 1
    assert h.estado == "CONFIRMADA"
    assert p.descripcion == "pendiente"
