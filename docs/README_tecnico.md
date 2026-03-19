# README técnico

## Propósito

Este documento resume el uso técnico mínimo del repositorio activo. El producto es una **aplicación desktop en Python + PySide6**; la documentación y los comandos deben reflejar ese alcance real.

## Requisitos

- Python 3.11+
- Dependencias de `requirements.txt` y `requirements-dev.txt`
- Entorno capaz de ejecutar PySide6 para las pruebas UI reales

## Instalación

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Arranque

```bash
python -m app
```

## Gates y validación

### Gate canónico de PR

```bash
python -m scripts.gate_pr
```

### Gate rápido

```bash
python -m scripts.gate_rapido
```

### Compatibilidad operativa

```bash
python scripts/quality_gate.py
python scripts/preflight_tests.py
python scripts/coverage_summary.py
python scripts/report_quality.py
```

## Pruebas

```bash
pytest -q -m "not ui"
pytest -q tests/golden/botones
```

## Estructura viva

- `app/domain`: reglas de negocio puras.
- `app/application`: casos de uso y orquestación.
- `app/infrastructure`: SQLite, filesystem, Google Sheets y adaptadores.
- `app/ui`: ventanas, diálogos, builders y presenters Qt.
- `scripts`: gates, auditorías y automatización de soporte.
- `tests`: contratos, regresiones, golden tests y pruebas de integración.

## UI

- [`ui/navigation.md`](ui/navigation.md)
- [`ui/main_window_modular.md`](ui/main_window_modular.md)

## Sincronización con Google Sheets

Resumen operativo:

1. Configurar credenciales y parámetros locales.
2. Verificar preflight y permisos.
3. Ejecutar la sincronización desde la UI o desde los casos de uso.
4. Revisar reportes y logs generados en `logs/`.

Referencia extendida:

- [`sincronizacion_google_sheets.md`](sincronizacion_google_sheets.md)
- [`api_sync_module.md`](api_sync_module.md)
