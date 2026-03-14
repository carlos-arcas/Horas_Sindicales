from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.orquestacion_confirmacion import confirmar_lote_y_generar_pdf


def _solicitud() -> SolicitudDTO:
    return SolicitudDTO(
        id=1,
        persona_id=10,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
    )


class _FsDummy:
    def mkdir(self, *_args, **_kwargs) -> None:
        return None

    def existe(self, _ruta: Path) -> bool:
        return False


class _GeneradorDummy:
    pass


def test_confirmar_lote_y_generar_pdf_respeta_orden_insertar_antes_pdf() -> None:
    eventos: list[str] = []

    def _resolver_destino(destino: Path, overwrite: bool, auto_rename: bool):
        _ = (overwrite, auto_rename)
        return type("Resolucion", (), {
            "ruta_destino": destino,
            "colision_detectada": False,
            "ruta_original": destino,
            "ruta_alternativa": None,
        })()

    def _validar(_solicitud: SolicitudDTO) -> None:
        return None

    def _confirmar(_solicitudes: list[SolicitudDTO], correlation_id: str | None = None):
        _ = correlation_id
        eventos.append("insertar_historico")
        return [_solicitud()], [], []

    def _generar(_creadas: list[SolicitudDTO], _destino: Path, correlation_id: str | None = None):
        _ = correlation_id
        eventos.append("generar_pdf")
        return Path("/tmp/salida.pdf"), _creadas

    creadas, pendientes, errores, pdf = confirmar_lote_y_generar_pdf(
        solicitudes=[_solicitud()],
        destino=Path("/tmp/salida.pdf"),
        resolver_destino_pdf=_resolver_destino,
        fs=_FsDummy(),
        generador_pdf=_GeneradorDummy(),
        validar_solicitud=_validar,
        confirmar_solicitudes_lote=_confirmar,
        generar_pdf_confirmadas=_generar,
        logger=__import__("logging").getLogger(__name__),
        correlation_id="corr-1",
    )

    assert len(creadas) == 1
    assert pendientes == []
    assert errores == []
    assert pdf == Path("/tmp/salida.pdf")
    assert eventos == ["insertar_historico", "generar_pdf"]


def test_confirmar_lote_con_error_de_insercion_no_genera_pdf() -> None:
    llamadas_generar = 0

    def _resolver_destino(destino: Path, overwrite: bool, auto_rename: bool):
        _ = (overwrite, auto_rename)
        return type("Resolucion", (), {
            "ruta_destino": destino,
            "colision_detectada": False,
            "ruta_original": destino,
            "ruta_alternativa": None,
        })()

    def _validar(_solicitud: SolicitudDTO) -> None:
        return None

    def _confirmar(_solicitudes: list[SolicitudDTO], correlation_id: str | None = None):
        _ = correlation_id
        return [], [_solicitud()], ["error_insertar"]

    def _generar(_creadas: list[SolicitudDTO], _destino: Path, correlation_id: str | None = None):
        nonlocal llamadas_generar
        _ = correlation_id
        llamadas_generar += 1
        return Path("/tmp/no_deberia.pdf"), _creadas

    creadas, pendientes, errores, pdf = confirmar_lote_y_generar_pdf(
        solicitudes=[_solicitud()],
        destino=Path("/tmp/salida.pdf"),
        resolver_destino_pdf=_resolver_destino,
        fs=_FsDummy(),
        generador_pdf=_GeneradorDummy(),
        validar_solicitud=_validar,
        confirmar_solicitudes_lote=_confirmar,
        generar_pdf_confirmadas=_generar,
        logger=__import__("logging").getLogger(__name__),
        correlation_id="corr-1",
    )

    assert creadas == []
    assert len(pendientes) == 1
    assert errores == ["error_insertar"]
    assert pdf is None
    assert llamadas_generar == 0
