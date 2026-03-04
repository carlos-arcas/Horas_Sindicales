from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.reportes_contenido import (
    ErrorDetalleDemasiadoLargo,
    ErrorIdentificadorVacio,
    ErrorMotivoReporteInvalido,
    ErrorPaginacionInvalida,
    ErrorTipoRecursoInvalido,
    PeticionPaginada,
    ReporteContenido,
)


def test_reporte_con_catalogos_validos() -> None:
    reporte = ReporteContenido(
        reporte_id="rep-1",
        denunciante_id="usr-1",
        recurso_tipo="publicacion",
        recurso_id="rec-1",
        motivo="spam",
        detalle="  texto ",
        estado="pendiente",
        creado_en=datetime.now(timezone.utc),
    )
    assert reporte.detalle == "texto"


@pytest.mark.parametrize(
    ("campo", "valor", "error"),
    [
        ("recurso_tipo", "archivo", ErrorTipoRecursoInvalido),
        ("motivo", "engaño", ErrorMotivoReporteInvalido),
    ],
)
def test_falla_catalogo_invalido(campo: str, valor: str, error: type[Exception]) -> None:
    kwargs = {
        "reporte_id": "rep-1",
        "denunciante_id": "usr-1",
        "recurso_tipo": "publicacion",
        "recurso_id": "rec-1",
        "motivo": "spam",
        "detalle": None,
        "estado": "pendiente",
        "creado_en": datetime.now(timezone.utc),
    }
    kwargs[campo] = valor
    with pytest.raises(error):
        ReporteContenido(**kwargs)


def test_falla_detalle_supera_maximo() -> None:
    with pytest.raises(ErrorDetalleDemasiadoLargo):
        ReporteContenido(
            reporte_id="rep-1",
            denunciante_id="usr-1",
            recurso_tipo="comentario",
            recurso_id="rec-1",
            motivo="otro",
            detalle="x" * 501,
            estado="pendiente",
            creado_en=datetime.now(timezone.utc),
        )


def test_falla_ids_vacios() -> None:
    with pytest.raises(ErrorIdentificadorVacio):
        ReporteContenido(
            reporte_id=" ",
            denunciante_id="usr-1",
            recurso_tipo="comentario",
            recurso_id="rec-1",
            motivo="otro",
            detalle=None,
            estado="pendiente",
            creado_en=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize("limit,offset", [(0, 0), (51, 0), (10, -1)])
def test_paginacion_invalida(limit: int, offset: int) -> None:
    with pytest.raises(ErrorPaginacionInvalida):
        PeticionPaginada(limit=limit, offset=offset)
