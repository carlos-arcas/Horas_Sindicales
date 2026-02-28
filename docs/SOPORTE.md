# Soporte (runbook)

## Diagnóstico rápido

1. Reproducir en local con el mismo comando del usuario.
2. Revisar logs de ejecución en `logs/`.
3. Confirmar estado de base local y migraciones.
4. Reintentar con `pytest -q -m "not ui"` para descartar regresión funcional.

## Errores típicos

### 1) Problemas de entorno Python

- Síntoma: import errors o arranque fallido.
- Acción: reinstalar dependencias con `requirements.txt` y `requirements-dev.txt`.

### 2) Sincronización con Sheets falla

- Síntoma: timeout, auth error o conflictos inesperados.
- Acción: validar credenciales/configuración y revisar guías de sync.
- Referencia: [`README_tecnico.md`](README_tecnico.md#sincronización-con-google-sheets).

### 3) Fallo en generación de PDF

- Síntoma: excepción al confirmar solicitud.
- Acción: comprobar datos obligatorios y recursos disponibles.

### 4) Fallo de tests en CI

- Síntoma: pipeline en rojo por lint o tests no UI.
- Acción: ejecutar localmente `ruff check .` y `pytest -q -m "not ui"`.

## Escalado

- Si no hay reproducción local fiable, abrir incidencia con pasos, logs y commit sospechoso.
- Si impacta release, bloquear publicación y priorizar fix + test de regresión.
