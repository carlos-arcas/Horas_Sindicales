# Horas Sindicales

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

Aplicación de escritorio (PySide6) para gestionar solicitudes de horas sindicales, generar PDFs y sincronizar datos con Google Sheets.

## Ejecutar en local (3 comandos)

```bash
python -m pip install -r requirements-dev.txt
python -m app
python -m app.entrypoints.cli_auditoria --help
```

## Ejecutar tests

```bash
pytest -q -m "not ui"
```

## Quality Gate

Comandos de ejecución del quality gate unificado:

- **Windows**

  ```bat
  quality_gate.bat
  ```

- **CLI (Python)**

  ```bash
  python scripts/quality_gate.py
  ```

Valida automáticamente:

- Coverage del core.
- Presupuesto de complejidad ciclomática (CC targets).
- Regresión de naming (baseline + nuevos offenders).
- Secretos en repositorio.
- Contrato de arquitectura.
- Contrato de release build.

Modo degradado (solo cuando falta `pytest-cov`):

```bash
python scripts/quality_gate.py --allow-missing-pytest-cov
```

> En modo degradado el estado global **siempre será FAIL** (coverage queda en `SKIP`), por lo que no equivale a un PASS de calidad.

## Configuración de sincronización

Consulta la sección de sincronización en la guía técnica:

- [`docs/README_tecnico.md`](docs/README_tecnico.md#sincronización-con-google-sheets)

## Documentación pública

- Guía técnica: [`docs/README_tecnico.md`](docs/README_tecnico.md)
- Decisiones técnicas: [`docs/DECISIONES_TECNICAS.md`](docs/DECISIONES_TECNICAS.md)
- Soporte y runbook: [`docs/SOPORTE.md`](docs/SOPORTE.md)

## Migración automática de claves i18n estables

Para generar el catálogo estable y el mapa de compatibilidad legacy desde `.config/ui_strings_baseline.json`:

```bash
python scripts/migrar_ui_strings_baseline.py
```

El script actualiza:
- `configuracion/i18n/es.json`
- `configuracion/i18n/_legacy_map.json`

## Endpoints de reportes y moderación (backoffice)

> Módulo técnico orientado a integración API. Implementa contratos para:
>
> - `POST /api/reportes/` (crear reporte idempotente).
> - `GET /api/admin/reportes/` (listado con filtros + paginación).
> - `POST /api/admin/reportes/<reporte_id>/resolver/` (descartar u ocultar recurso).
>
> En este repositorio se entrega la base de dominio/aplicación/infraestructura SQLite para soportar estos flujos y su auditoría de seguridad.
