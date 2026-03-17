from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.application.conflicts_service import ConflictsService
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases import CargarDatosDemoCasoUso
from app.application.use_cases.exportar_compartir_periodo import (
    ExportarCompartirPeriodoCasoUso,
)
from app.application.use_cases.grupos_config import GrupoConfigUseCases
from app.application.use_cases.personas import PersonaUseCases
from app.application.use_cases.solicitudes import SolicitudUseCases
from app.application.use_cases.validacion_preventiva_lock_use_case import (
    ValidacionPreventivaLockUseCase,
)
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.confirmacion_pdf.caso_uso import (
    ConfirmarPendientesPdfCasoUso,
)
from app.application.use_cases.confirmacion_pdf.coordinador_confirmacion_pdf import (
    CoordinadorConfirmacionPdf,
)
from app.application.use_cases.confirmacion_pdf.servicio_destino_pdf_confirmacion import (
    ServicioDestinoPdfConfirmacion,
)
from app.application.use_cases.confirmacion_pdf.generar_pdf_confirmadas_caso_uso import (
    GenerarPdfSolicitudesConfirmadasCasoUso,
)
from app.application.use_cases.politica_modo_solo_lectura import (
    configurar_proveedor_modo_solo_lectura,
)
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    CrearPendienteCasoUso,
    SolicitudCrearPendientePeticion,
)
from app.application.use_cases.health_check import HealthCheckUseCase
from app.infrastructure.cargador_datos_demo_sqlite import CargadorDatosDemoSQLite
from app.infrastructure.confirmacion_pdf.adaptadores import (
    GeneradorPdfConfirmadasDesdeCasosUso,
    RepositorioSolicitudesDesdeCasosUso,
)
from app.infrastructure.db import _default_db_path, get_connection
from app.infrastructure.health_probes import (
    DefaultConnectivityProbe,
    SheetsConfigProbe,
    SQLiteLocalDbProbe,
)
from app.infrastructure.i18n import CargadorI18nDesdeArchivos, ServicioI18nEstable
from app.infrastructure.local_config import RepositorioPreferenciasIni
from app.infrastructure.auditoria_e2e.adaptadores import RelojSistema
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal
from app.infrastructure.local_config_store import LocalConfigStore
from app.infrastructure.migrations import run_migrations
from app.infrastructure.pdf.generador_pdf_reportlab import GeneradorPdfReportlab
from app.infrastructure.proveedor_dataset_demo import ProveedorDatasetDemo
from app.infrastructure.repos_conflicts_sqlite import SQLiteConflictsRepository
from app.infrastructure.repos_sqlite import (
    CuadranteRepositorySQLite,
    GrupoConfigRepositorySQLite,
    RepositorioPersonasSQLite,
    SolicitudRepositorySQLite,
)
from app.infrastructure.seed import seed_if_empty
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_gateway_gspread import SheetsGatewayGspread
from app.infrastructure.sheets_repository import SheetsRepository
from app.infrastructure.sqlite_lock_error_classifier import SQLiteLockErrorClassifier
from app.infrastructure.sync_sheets_adapter import SyncSheetsAdapter
from app.configuracion.settings import is_read_only_enabled
from aplicacion.puertos.proveedor_i18n import ProveedorI18N
from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias

LOGGER = logging.getLogger(__name__)


@dataclass
class AppContainer:
    persona_use_cases: PersonaUseCases
    solicitud_use_cases: SolicitudUseCases
    grupo_use_cases: GrupoConfigUseCases
    sheets_service: SheetsService
    sync_service: SyncSheetsUseCase
    conflicts_service: ConflictsService
    health_check_use_case: HealthCheckUseCase
    alert_engine: AlertEngine
    validacion_preventiva_lock_use_case: ValidacionPreventivaLockUseCase
    confirmar_pendientes_pdf_caso_uso: ConfirmarPendientesPdfCasoUso
    coordinador_confirmacion_pdf: CoordinadorConfirmacionPdf
    servicio_destino_pdf_confirmacion: ServicioDestinoPdfConfirmacion
    crear_pendiente_caso_uso: CrearPendienteCasoUso
    repositorio_preferencias: IRepositorioPreferencias
    cargar_datos_demo_caso_uso: CargarDatosDemoCasoUso
    exportar_compartir_periodo_caso_uso: ExportarCompartirPeriodoCasoUso
    servicio_i18n: ProveedorI18N


ConnectionFactory = Callable[[], object]


def build_container(
    connection_factory: ConnectionFactory = get_connection,
    *,
    preferencias_headless: bool = True,
) -> AppContainer:
    configurar_proveedor_modo_solo_lectura(is_read_only_enabled)

    connection = connection_factory()
    run_migrations(connection)
    seed_if_empty(connection)

    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    grupo_repo = GrupoConfigRepositorySQLite(connection)
    cuadrante_repo = CuadranteRepositorySQLite(connection)

    base_cuadrantes_service = BaseCuadrantesService(persona_repo, cuadrante_repo)
    base_cuadrantes_service.ensure_for_all_personas()
    persona_use_cases = PersonaUseCases(persona_repo, base_cuadrantes_service)
    generador_pdf = GeneradorPdfReportlab()
    solicitud_use_cases = SolicitudUseCases(
        solicitud_repo,
        persona_repo,
        fs=SistemaArchivosLocal(),
        config_repo=grupo_repo,
        generador_pdf=generador_pdf,
    )
    generador_pdf_confirmadas_caso_uso = GenerarPdfSolicitudesConfirmadasCasoUso(
        repo=solicitud_repo,
        persona_repo=persona_repo,
        config_repo=grupo_repo,
        generador_pdf=generador_pdf,
    )
    repositorio_solicitudes_confirmacion_pdf = RepositorioSolicitudesDesdeCasosUso(
        solicitud_use_cases
    )
    confirmar_pendientes_pdf_caso_uso = ConfirmarPendientesPdfCasoUso(
        repositorio=repositorio_solicitudes_confirmacion_pdf,
        generador_pdf=GeneradorPdfConfirmadasDesdeCasosUso(
            generador_pdf_confirmadas_caso_uso
        ),
        sistema_archivos=SistemaArchivosLocal(),
    )
    crear_pendiente_caso_uso = CrearPendienteCasoUso(
        repositorio=RepositorioSolicitudesDesdeCasosUso(solicitud_use_cases)
    )

    def crear_pendiente_para_confirmacion_pdf(solicitud, *, correlation_id=None):
        resultado = crear_pendiente_caso_uso.execute(
            SolicitudCrearPendientePeticion(
                solicitud=solicitud,
                correlation_id=correlation_id,
            )
        )
        if resultado.solicitud_creada is None:
            raise ValueError(resultado.errores[0] if resultado.errores else "No se pudo crear la solicitud pendiente.")
        return resultado.solicitud_creada

    coordinador_confirmacion_pdf = CoordinadorConfirmacionPdf(
        repo=solicitud_repo,
        persona_repo=persona_repo,
        fs=SistemaArchivosLocal(),
        config_repo=grupo_repo,
        generador_pdf=generador_pdf,
        crear_pendiente=crear_pendiente_para_confirmacion_pdf,
        logger=LOGGER,
    )
    servicio_destino_pdf_confirmacion = ServicioDestinoPdfConfirmacion(
        persona_repo=persona_repo,
        fs=SistemaArchivosLocal(),
        generador_pdf=generador_pdf,
    )

    grupo_use_cases = GrupoConfigUseCases(grupo_repo)

    config_store = LocalConfigStore()
    sheets_client = SheetsClient()
    sheets_repository = SheetsRepository()
    sheets_gateway = SheetsGatewayGspread(sheets_client, sheets_repository)
    sheets_service = SheetsService(config_store, sheets_gateway)

    sync_port = SyncSheetsAdapter(
        connection_factory, config_store, sheets_client, sheets_repository
    )
    sync_service = SyncSheetsUseCase(sync_port)

    health_check_use_case = HealthCheckUseCase(
        SheetsConfigProbe(config_store, sheets_client),
        DefaultConnectivityProbe(),
        SQLiteLocalDbProbe(connection_factory),
    )
    alert_engine = AlertEngine()
    validacion_preventiva_lock_use_case = ValidacionPreventivaLockUseCase(
        SQLiteLockErrorClassifier()
    )

    repositorio_preferencias = _build_repositorio_preferencias(
        preferencias_headless=preferencias_headless
    )

    conflicts_repository = SQLiteConflictsRepository(connection)
    conflicts_service = ConflictsService(
        conflicts_repository,
        lambda: config_store.load().device_id if config_store.load() else "",
    )

    proveedor_dataset_demo = ProveedorDatasetDemo()
    cargador_demo = CargadorDatosDemoSQLite(proveedor_dataset_demo, _default_db_path())
    cargar_datos_demo_caso_uso = CargarDatosDemoCasoUso(cargador_demo)
    exportar_compartir_periodo_caso_uso = ExportarCompartirPeriodoCasoUso(
        fs=SistemaArchivosLocal(),
        reloj=RelojSistema(),
        exportador_pdf=generador_pdf,
    )
    cargador_i18n = CargadorI18nDesdeArchivos(Path("configuracion") / "i18n")
    servicio_i18n = ServicioI18nEstable(
        cargador_i18n.cargar_catalogos(),
        mapa_legacy=cargador_i18n.cargar_mapa_legacy(),
    )

    return AppContainer(
        persona_use_cases=persona_use_cases,
        solicitud_use_cases=solicitud_use_cases,
        grupo_use_cases=grupo_use_cases,
        sheets_service=sheets_service,
        sync_service=sync_service,
        conflicts_service=conflicts_service,
        health_check_use_case=health_check_use_case,
        alert_engine=alert_engine,
        validacion_preventiva_lock_use_case=validacion_preventiva_lock_use_case,
        confirmar_pendientes_pdf_caso_uso=confirmar_pendientes_pdf_caso_uso,
        coordinador_confirmacion_pdf=coordinador_confirmacion_pdf,
        servicio_destino_pdf_confirmacion=servicio_destino_pdf_confirmacion,
        crear_pendiente_caso_uso=crear_pendiente_caso_uso,
        repositorio_preferencias=repositorio_preferencias,
        cargar_datos_demo_caso_uso=cargar_datos_demo_caso_uso,
        exportar_compartir_periodo_caso_uso=exportar_compartir_periodo_caso_uso,
        servicio_i18n=servicio_i18n,
    )


def _build_repositorio_preferencias(
    *, preferencias_headless: bool = False
) -> IRepositorioPreferencias:
    if preferencias_headless:
        return RepositorioPreferenciasIni()
    try:
        modulo = importlib.import_module(
            "infraestructura.repositorio_preferencias_qsettings"
        )
        repositorio_cls = modulo.RepositorioPreferenciasQSettings
        return repositorio_cls()
    except (ImportError, AttributeError) as exc:
        LOGGER.warning(
            "No se pudo cargar QSettings; se usa persistencia headless INI.",
            extra={
                "extra": {
                    "fallback": "RepositorioPreferenciasIni",
                    "motivo": str(exc),
                }
            },
        )
        return RepositorioPreferenciasIni()
