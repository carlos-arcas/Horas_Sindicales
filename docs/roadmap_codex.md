# Roadmap Codex

> Documento operativo derivado de `docs/features.json`.
> No sustituye la fuente de verdad ni redefine estados funcionales.

Fecha de actualizacion: 2026-03-26

## Fuente de verdad

- Fuente unica de backlog y estados: `docs/features.json`
- Documentos derivados contractuales: `docs/features.md` y `docs/features_pendientes.md`
- Este roadmap solo registra la tarea activa y el orden operativo seguido por el agente.

## Tarea activa

### FTR-006 - Corregir fallo reproducible del gate rapido en entorno local

- Estado operativo: `BLOQUEADO/NO VERIFICABLE`
- Prioridad: `1`
- Alcance de esta ejecucion: identificar el primer comando que rompe en `python -m scripts.gate_rapido` y aplicar el fix minimo para arrancar el gate desde el entorno local del repo.
- Evidencia inicial:
  - `python -m scripts.gate_rapido` falla en el primer paso.
  - Error observado: `No module named ruff`.
- Cambios validados:
  - Los gates priorizan el Python del repo (`.venv`) cuando existe.
  - `gate_rapido` ejecuta los subruns `pytest` con harness `core-no-ui`.
  - La auditoria E2E normaliza rutas con separador POSIX en la evidencia.
- Estado final de esta ejecucion:
  - `ruff check` focal: PASS.
  - `pytest` focal de herramientas y auditoria E2E: PASS.
  - `python -m scripts.gate_rapido`: bloqueado por `PermissionError [WinError 5]` en temporales de `pytest`.
  - `python -m scripts.gate_pr`: bloqueado/no verificable por el mismo motivo y por residuos temporales inaccesibles generados por `pytest`.
- Siguiente accion exacta recomendada:
  - Recuperar o limpiar desde Windows los directorios temporales inaccesibles `pytest-cache-files-*`, `tmp*` y los probes bajo `logs/`.
  - Reintentar `python -m scripts.gate_rapido`.
  - Si queda en verde, ejecutar `python -m scripts.gate_pr`.
- Restricciones:
  - No tocar CI.
  - No expandir a otras features.
  - Cambios pequenos y reversibles.

## Cola derivada de features.json

1. `FTR-006` - TODO - prioridad 1
2. `FTR-007` - TODO - prioridad 2
3. `FTR-008` - TODO - prioridad 3
4. `FTR-009` - TODO - prioridad 4
5. `FTR-010` - TODO - prioridad 5
