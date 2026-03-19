# Horas Sindicales

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

Horas Sindicales es una **aplicación de escritorio en Python + PySide6** para registrar solicitudes sindicales, generar PDFs y sincronizar datos con Google Sheets.

## Qué sí es este repositorio

- App desktop con interfaz Qt (`PySide6`).
- Núcleo de negocio separado por capas (`app/domain`, `app/application`, `app/infrastructure`, `app/ui`).
- Persistencia local SQLite y adaptadores de integración.
- Scripts operativos para Windows y gates reproducibles en Python.

## Qué no es este repositorio

- No es una interfaz pensada para navegador.
- No es un servicio HTTP multiusuario.
- No usa un stack web heredado como definición del producto.
- No expone una API HTTP como definición principal del sistema.

## Ejecutar en local

```bash
python -m pip install -r requirements-dev.txt
python -m app
```

## Ejecutar tests

```bash
pytest -q -m "not ui"
```

## Quality Gate

Comandos oficiales del gate:

- **Windows**

  ```bat
  quality_gate.bat
  ```

- **CLI canónico para PR**

  ```bash
  python -m scripts.gate_pr
  ```

- **Gate rápido**

  ```bash
  python -m scripts.gate_rapido
  ```

Compatibilidad operativa/documental:

```bash
python scripts/quality_gate.py
python scripts/quality_gate.py --allow-missing-pytest-cov
```

> En `scripts/quality_gate.py` el **estado global** sigue siendo **FAIL** cuando falta cobertura, aunque se use el modo degradado. Ese comando se mantiene por compatibilidad operativa; el gate contractual del repositorio es `python -m scripts.gate_pr`.

## Entrypoints oficiales

### Windows

- `lanzar_app.bat`
- `ejecutar_tests.bat`
- `quality_gate.bat`
- `auditar_e2e.bat`
- `launcher.bat`
- `setup.bat`
- `update.bat`

### Python / CLI

- `python -m app`
- `python -m app.entrypoints.cli_auditoria --dry-run`
- `python -m app.entrypoints.cli_auditoria --write`
- `python -m scripts.gate_rapido`
- `python -m scripts.gate_pr`

## Documentación útil

- Índice documental: [`docs/README.md`](docs/README.md)
- Arquitectura: [`docs/arquitectura.md`](docs/arquitectura.md)
- Decisiones técnicas: [`docs/decisiones_tecnicas.md`](docs/decisiones_tecnicas.md)
- Guía de pruebas: [`docs/guia_pruebas.md`](docs/guia_pruebas.md)
- Guía de logging: [`docs/guia_logging.md`](docs/guia_logging.md)
- Definición del producto: [`docs/definicion_producto_final.md`](docs/definicion_producto_final.md)
- Soporte técnico: [`docs/SOPORTE.md`](docs/SOPORTE.md)

## Sincronización con Google Sheets

La configuración y el flujo operativo están documentados en:

- [`docs/README_tecnico.md`](docs/README_tecnico.md#sincronización-con-google-sheets)
- [`docs/sincronizacion_google_sheets.md`](docs/sincronizacion_google_sheets.md)

## Regla de mantenimiento

Si un archivo, script o documento no ayuda a ejecutar la app, mantenerla, probarla o auditarla, no debería vivir en la cara activa del repositorio.
