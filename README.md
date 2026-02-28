# Horas Sindicales

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

## Configuración de sincronización

Consulta la sección de sincronización en la guía técnica:

- [`docs/README_tecnico.md`](docs/README_tecnico.md#sincronización-con-google-sheets)

## Documentación pública

- Guía técnica: [`docs/README_tecnico.md`](docs/README_tecnico.md)
- Decisiones técnicas: [`docs/DECISIONES_TECNICAS.md`](docs/DECISIONES_TECNICAS.md)
- Soporte y runbook: [`docs/SOPORTE.md`](docs/SOPORTE.md)
