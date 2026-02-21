# Stub de auditoría (deprecado en raíz)

Este archivo es un **stub** y no contiene auditoría manual.

La auditoría oficial se genera automáticamente por el Auditor E2E.

## Cómo generar la auditoría real

1. Ejecuta el pipeline de calidad en Windows con `quality_gate.bat`.
2. O ejecuta directamente:
   `python -m app.entrypoints.cli_auditoria --write`
3. Revisa los artefactos en `logs/evidencias/<ID>/`.

## Archivos canónicos generados

- `AUDITORIA.md`
- `auditoria.json`
- `manifest.json`
- `status.txt`

Generado por política: **Prohibido generar informes manuales**.
