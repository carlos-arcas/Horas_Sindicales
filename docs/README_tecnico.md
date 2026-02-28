# README técnico

## Requisitos

- Python 3.11+
- Dependencias de `requirements.txt` y `requirements-dev.txt`

## Instalación

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Desarrollo

### Ejecutar aplicación

```bash
python -m app
```

### Auditoría por CLI

```bash
python -m app.entrypoints.cli_auditoria --help
```

### Calidad y tests

```bash
ruff check .
pytest -q -m "not ui"
```

## Comandos útiles

- `python scripts/quality_gate.py`
- `python scripts/preflight_tests.py`
- `python scripts/coverage_summary.py`
- `python scripts/report_quality.py`

## Sincronización con Google Sheets

Resumen operativo:

1. Configura credenciales y parámetros locales.
2. Verifica precondiciones de red/API.
3. Ejecuta sincronización desde UI o desde casos de uso de aplicación.

Referencia extendida:

- [`sincronizacion_google_sheets.md`](sincronizacion_google_sheets.md)
- [`api_sync_module.md`](api_sync_module.md)
