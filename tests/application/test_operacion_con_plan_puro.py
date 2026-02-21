from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.puertos import RepoInfo
from app.application.dto import SolicitudDTO
from app.application.operaciones.auditoria_e2e_operacion import OperacionAuditoriaE2E, RequestOperacionAuditoria
from app.application.operaciones.exportacion_pdf_historico_operacion import (
    ExportacionPdfHistoricoOperacion,
    RequestExportacionPdfHistorico,
)
from app.domain.models import Persona


class FSSpySinWrites:
    def __init__(self) -> None:
        self.write_calls = 0

    def existe(self, ruta: Path) -> bool:
        return False

    def leer_texto(self, ruta: Path) -> str:
        return ""

    def leer_bytes(self, ruta: Path) -> bytes:
        return b""

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        self.write_calls += 1
        raise AssertionError("No debe escribir en métodos de preflight")

    def escribir_bytes(self, ruta: Path, contenido: bytes) -> None:
        self.write_calls += 1
        raise AssertionError("No debe escribir en métodos de preflight")

    def mkdir(self, ruta: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        _ = (parents, exist_ok)
        self.write_calls += 1
        raise AssertionError("No debe crear directorios en métodos de preflight")

    def listar(self, base: Path) -> list[Path]:
        return []

    def listar_python(self, base: Path) -> list[Path]:
        return []

    def mkdirs(self, ruta: Path) -> None:
        self.write_calls += 1
        raise AssertionError("No debe crear directorios en métodos de preflight")


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2026, 2, 20, 10, 30, 0, tzinfo=timezone.utc)


class HashFijo:
    def sha256_texto(self, contenido: str) -> str:
        return "abc12345" * 8


class RepoFijo:
    def obtener_info(self) -> RepoInfo:
        return RepoInfo(root=Path("/repo"), branch="main", commit="deadbee")


class GeneradorPdfDummy:
    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: list[str]) -> str:
        _ = (nombre_solicitante, fechas)
        return "dummy.pdf"

    def generar_pdf_solicitudes(self, solicitudes, persona, destino, intro_text=None, logo_path=None, include_hours_in_horario=None):
        raise AssertionError("No debe ejecutarse en test puro")

    def generar_pdf_historico(self, solicitudes, persona, destino, intro_text=None, logo_path=None):
        raise AssertionError("No debe ejecutarse en test puro")


def _persona() -> Persona:
    return Persona(
        id=1,
        nombre="Delegada Demo",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=True,
        cuad_lun_man_min=240,
        cuad_lun_tar_min=240,
        cuad_mar_man_min=240,
        cuad_mar_tar_min=240,
        cuad_mie_man_min=240,
        cuad_mie_tar_min=240,
        cuad_jue_man_min=240,
        cuad_jue_tar_min=240,
        cuad_vie_man_min=240,
        cuad_vie_tar_min=240,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_preflight_operaciones_no_hace_writes() -> None:
    fs = FSSpySinWrites()

    auditor = AuditarE2E(reloj=RelojFijo(), fs=fs, repo_info=RepoFijo(), hasher=HashFijo())
    op_auditoria = OperacionAuditoriaE2E(auditor)
    plan_auditoria = op_auditoria.obtener_plan(RequestOperacionAuditoria(dry_run=True, id_auditoria="AUD-PLAN-1"))
    op_auditoria.obtener_rutas(plan_auditoria)
    op_auditoria.validar_conflictos(plan_auditoria)

    op_pdf = ExportacionPdfHistoricoOperacion(fs=fs, generador_pdf=GeneradorPdfDummy())
    solicitud = SolicitudDTO(
        id=1,
        persona_id=1,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
    )
    plan_pdf = op_pdf.obtener_plan(
        RequestExportacionPdfHistorico(
            solicitudes=[solicitud],
            persona=_persona(),
            destino=Path("/tmp/historico.pdf"),
            dry_run=True,
        )
    )
    op_pdf.obtener_rutas(plan_pdf)
    op_pdf.validar_conflictos(plan_pdf)

    assert fs.write_calls == 0
