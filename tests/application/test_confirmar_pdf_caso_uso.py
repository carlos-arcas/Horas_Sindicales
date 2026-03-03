from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.caso_uso import ConfirmarPendientesPdfCasoUso
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion


class FakeRepositorio:
    def __init__(self, pendientes: list[SolicitudDTO]) -> None:
        self._pendientes = pendientes
        self.confirmar_sin_pdf_calls = 0

    def listar_pendientes(self) -> list[SolicitudDTO]:
        return list(self._pendientes)

    def confirmar_sin_pdf(self, pendientes: list[SolicitudDTO], correlation_id: str | None = None):
        self.confirmar_sin_pdf_calls += 1
        ids = {sol.id for sol in pendientes}
        creadas = [sol for sol in self._pendientes if sol.id in ids]
        restantes = [sol for sol in self._pendientes if sol.id not in ids]
        self._pendientes = restantes
        return creadas, restantes, []


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


def test_caso_ok_con_pdf() -> None:
    repo = FakeRepositorio([_solicitud(1), _solicitud(2)])
    generador = FakeGeneradorPdf()
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, generador, fs)

    result = caso_uso.execute(
        SolicitudConfirmarPdfPeticion(pendientes_ids=[1], generar_pdf=True, destino_pdf=Path("/tmp/salida.pdf"))
    )

    assert result.ruta_pdf == Path("/tmp/salida.pdf")
    assert result.confirmadas_ids == [1]
    assert result.errores == []


def test_caso_error_seleccion_vacia() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    generador = FakeGeneradorPdf()
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, generador, fs)

    result = caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[], generar_pdf=True, destino_pdf=Path("/tmp/a.pdf")))

    assert result.confirmadas_ids == []
    assert result.errores
    assert repo.confirmar_sin_pdf_calls == 0
    assert generador.calls == 0


def test_caso_error_pdf_sin_destino() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    generador = FakeGeneradorPdf()
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, generador, fs)

    result = caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[1], generar_pdf=True, destino_pdf=None))

    assert result.errores
    assert generador.calls == 0


def test_caso_ok_sin_pdf() -> None:
    repo = FakeRepositorio([_solicitud(1), _solicitud(2)])
    generador = FakeGeneradorPdf()
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, generador, fs)

    result = caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[1, 2], generar_pdf=False))

    assert sorted(result.confirmadas_ids) == [1, 2]
    assert result.ruta_pdf is None
    assert generador.calls == 0


def test_preflight_no_toca_disco() -> None:
    repo = FakeRepositorio([_solicitud(1)])
    generador = FakeGeneradorPdf()
    fs = FakeFs()
    caso_uso = ConfirmarPendientesPdfCasoUso(repo, generador, fs)

    caso_uso.execute(SolicitudConfirmarPdfPeticion(pendientes_ids=[], generar_pdf=True, destino_pdf=None))

    assert fs.mkdir_calls == 0
