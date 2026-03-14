from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.caso_uso import ConfirmarPendientesPdfCasoUso
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion


class FakeRepositorio:
    def __init__(self, pendientes: list[SolicitudDTO]) -> None:
        self._pendientes = pendientes
        self.confirmar_sin_pdf_calls = 0
        self.force_insert_error = False
        self.force_pdf_error = False

    def listar_pendientes(self) -> list[SolicitudDTO]:
        return list(self._pendientes)

    def confirmar_sin_pdf(self, pendientes: list[SolicitudDTO], correlation_id: str | None = None):
        self.confirmar_sin_pdf_calls += 1
        ids = {sol.id for sol in pendientes}
        creadas = [sol for sol in self._pendientes if sol.id in ids]
        restantes = [sol for sol in self._pendientes if sol.id not in ids]
        self._pendientes = restantes
        if self.force_insert_error:
            return [], list(self._pendientes), ["error_insercion"]
        return creadas, restantes, []

    def confirmar_con_pdf(self, pendientes: list[SolicitudDTO], destino_pdf: Path, correlation_id: str | None = None):
        ids = [sol.id for sol in pendientes if sol.id is not None]
        if self.force_pdf_error:
            return None, ids, "error_pdf"
        self._pendientes = [sol for sol in self._pendientes if sol.id not in set(ids)]
        return destino_pdf, sorted(ids), "OK"


class FakeGeneradorPdf:
    def __init__(self) -> None:
        self.calls = 0

    def generar_pdf_pendientes(self, pendientes: list[SolicitudDTO], destino: Path, correlation_id: str | None = None):
        self.calls += 1
        return destino, [sol.id for sol in pendientes if sol.id is not None], "OK"


class FakeFs:
    def __init__(self) -> None:
        self.mkdir_calls = 0

    def mkdir(self, ruta: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        self.mkdir_calls += 1


def _solicitud(solicitud_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
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


def test_caso_correcto_contrato_tipado_ok_con_pdf() -> None:
    repo = FakeRepositorio([_solicitud(1), _solicitud(2)])
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), FakeFs())

    result = caso_uso.execute(
        SolicitudConfirmarPdfPeticion(pendientes_ids=[1], generar_pdf=True, destino_pdf=Path("/tmp/salida.pdf"))
    )

    assert result.estado == "OK_CON_PDF"
    assert result.confirmadas == 1
    assert result.confirmadas_ids == [1]
    assert result.pdf_generado == Path("/tmp/salida.pdf")
    assert result.sync_permitido is True
    assert result.errores == []


def test_caso_error_insercion_no_genera_pdf_ni_sync() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    repo.force_insert_error = True
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), FakeFs())

    result = caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[1], generar_pdf=False))

    assert result.estado == "ERROR_INSERCION"
    assert result.confirmadas == 0
    assert result.pdf_generado is None
    assert result.sync_permitido is False
    assert result.errores == ["error_insercion"]


def test_caso_error_pdf_no_habilita_sync() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    repo.force_pdf_error = True
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), FakeFs())

    result = caso_uso.execute(
        SolicitudConfirmarPdfPeticion(pendientes_ids=[1], generar_pdf=True, destino_pdf=Path("/tmp/fallo.pdf"))
    )

    assert result.estado == "ERROR_PDF"
    assert result.confirmadas == 1
    assert result.confirmadas_ids == [1]
    assert result.pdf_generado is None
    assert result.sync_permitido is False
    assert result.errores == ["error_pdf"]


def test_caso_sin_confirmadas_no_genera_pdf_ni_sync() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), FakeFs())

    result = caso_uso.execute(
        SolicitudConfirmarPdfPeticion(pendientes_ids=[999], generar_pdf=True, destino_pdf=Path("/tmp/none.pdf"))
    )

    assert result.estado == "ERROR_PRECONDICION"
    assert result.confirmadas == 0
    assert result.pdf_generado is None
    assert result.sync_permitido is False


def test_preflight_no_toca_disco() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), fs)

    caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[], generar_pdf=True, destino_pdf=None))

    assert fs.mkdir_calls == 0


def test_caso_uso_es_invocable_como_callable() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, FakeGeneradorPdf(), FakeFs())

    resultado = caso_uso(
        SolicitudConfirmarPdfPeticion(
            pendientes_ids=[1],
            generar_pdf=True,
            destino_pdf=Path("/tmp/callable.pdf"),
        )
    )

    assert resultado.estado == "OK_CON_PDF"
    assert resultado.pdf_generado == Path("/tmp/callable.pdf")
    assert resultado.confirmadas_ids == [1]
