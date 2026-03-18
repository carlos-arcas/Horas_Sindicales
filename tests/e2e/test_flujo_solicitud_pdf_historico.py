from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.politica_modo_solo_lectura import crear_estado_modo_solo_lectura, crear_politica_modo_solo_lectura
from app.application.use_cases.confirmacion_pdf.caso_uso import (
    ConfirmarPendientesPdfCasoUso,
)
from app.application.use_cases.confirmacion_pdf.modelos import (
    SolicitudConfirmarPdfPeticion,
)
from app.application.use_cases.confirmacion_pdf.generar_pdf_confirmadas_caso_uso import (
    GenerarPdfSolicitudesConfirmadasCasoUso,
)
from app.domain.models import Persona
from app.infrastructure.confirmacion_pdf.adaptadores import (
    GeneradorPdfConfirmadasDesdeCasosUso,
    RepositorioSolicitudesDesdeCasosUso,
)
from app.infrastructure.migrations import run_migrations
from app.infrastructure.pdf.generador_pdf_reportlab import GeneradorPdfReportlab
from app.infrastructure.repos_sqlite import (
    RepositorioPersonasSQLite,
    SolicitudRepositorySQLite,
)
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal


def test_flujo_solicitud_pdf_historico_contrato_prioridad_1(tmp_path: Path) -> None:
    ruta_db = tmp_path / "e2e_prioridad_1.sqlite3"
    destino_pdf = tmp_path / "salida_pdf" / "solicitudes_confirmadas.pdf"

    connection = sqlite3.connect(ruta_db)
    connection.row_factory = sqlite3.Row
    run_migrations(connection)

    try:
        persona_repo = RepositorioPersonasSQLite(connection)
        solicitud_repo = SolicitudRepositorySQLite(connection)
        fs_local = SistemaArchivosLocal()
        generador_pdf = GeneradorPdfReportlab()

        politica_modo_solo_lectura = crear_politica_modo_solo_lectura(crear_estado_modo_solo_lectura(lambda: False))
        solicitud_use_cases = SolicitudUseCases(
            solicitud_repo,
            persona_repo,
            generador_pdf=generador_pdf,
            fs=fs_local,
            politica_modo_solo_lectura=politica_modo_solo_lectura,
        )

        confirmacion_caso_uso = ConfirmarPendientesPdfCasoUso(
            repositorio=RepositorioSolicitudesDesdeCasosUso(solicitud_use_cases),
            generador_pdf=GeneradorPdfConfirmadasDesdeCasosUso(
                GenerarPdfSolicitudesConfirmadasCasoUso(
                    repo=solicitud_repo,
                    persona_repo=persona_repo,
                    generador_pdf=generador_pdf,
                )
            ),
            sistema_archivos=fs_local,
            politica_modo_solo_lectura=politica_modo_solo_lectura,
        )

        persona = persona_repo.create(
            Persona(
                id=None,
                nombre="Delegada E2E Contrato",
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
        )

        solicitud_creada, _ = solicitud_use_cases.agregar_solicitud(
            SolicitudDTO(
                id=None,
                persona_id=int(persona.id or 0),
                fecha_solicitud="2026-01-01",
                fecha_pedida="2026-01-15",
                desde="09:00",
                hasta="10:00",
                completo=False,
                horas=1.0,
                observaciones="flujo e2e",
                pdf_path=None,
                pdf_hash=None,
                notas="nota contrato",
            ),
            correlation_id="corr-e2e-prioridad-1-crear",
        )

        resultado_confirmacion = confirmacion_caso_uso.execute(
            SolicitudConfirmarPdfPeticion(
                pendientes_ids=[int(solicitud_creada.id or 0)],
                generar_pdf=True,
                destino_pdf=destino_pdf,
                correlation_id="corr-e2e-prioridad-1-confirmar",
            )
        )

        resultado_dict = asdict(resultado_confirmacion)
        resultado_dict["pdf_generado"] = (
            str(resultado_confirmacion.pdf_generado)
            if resultado_confirmacion.pdf_generado
            else None
        )
        (tmp_path / "resumen_confirmacion.json").write_text(
            json.dumps(
                {
                    **resultado_dict,
                    "ruta_pdf": str(resultado_confirmacion.ruta_pdf)
                    if resultado_confirmacion.ruta_pdf
                    else None,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        pendientes = list(solicitud_use_cases.listar_pendientes_all())
        historico = list(solicitud_use_cases.listar_historico())

        assert destino_pdf.exists()
        assert destino_pdf.stat().st_size > 0
        assert destino_pdf.read_bytes()[:4] == b"%PDF"

        assert all(item.id != solicitud_creada.id for item in pendientes)

        solicitud_historico = next(
            (item for item in historico if item.id == solicitud_creada.id), None
        )
        assert solicitud_historico is not None
        assert solicitud_historico.generated is True
        assert solicitud_historico.pdf_path
        assert Path(str(solicitud_historico.pdf_path)).exists()
    finally:
        connection.close()
