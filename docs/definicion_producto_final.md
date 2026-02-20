# Definición de producto final (checklist auditable)

## Uso

Este checklist sirve como evidencia mínima antes de declarar una entrega como "producto final" para release o auditoría interna.

## Checklist

### 1) Scripts y ejecución

- [ ] Existe script de arranque en Windows (`lanzar_app.bat` o equivalente vigente).
- [ ] Existe script de tests en Windows (`ejecutar_tests.bat`).
- [ ] Los comandos documentados en README funcionan en entorno limpio.

### 2) Pruebas y cobertura

- [ ] `pytest -q` pasa en entorno local/CI.
- [ ] Se ejecuta cobertura con `--cov` sobre `app`.
- [ ] Se cumple el umbral definido por la política de cobertura vigente.

### 3) Logging y trazabilidad

- [ ] Se generan `logs/seguimiento.log` y `logs/crashes.log`.
- [ ] El formato de logs es JSONL.
- [ ] Se puede rastrear una operación completa por `correlation_id`.

### 4) Documentación mínima

- [ ] `README.md` actualizado.
- [ ] `docs/arquitectura.md` actualizado.
- [ ] `docs/decisiones_tecnicas.md` actualizado.
- [ ] `docs/guia_pruebas.md` actualizado.
- [ ] `docs/guia_logging.md` actualizado.
- [ ] `docs/definicion_producto_final.md` actualizado.

### 5) Versionado y release

- [ ] `VERSION` consistente con release objetivo.
- [ ] `CHANGELOG.md` en raíz incluye entrada para la versión.
- [ ] Artefactos/snapshots de auditoría se guardan según proceso vigente.

## Criterio de salida

Se considera apto cuando todos los ítems aplicables están marcados y existe evidencia verificable (logs, reports, commits y/o artefactos de CI).

## Pendiente de completar

- Pendiente de completar plantilla de evidencia adjunta por cada ítem (URL CI, hash de artefacto, responsable).
