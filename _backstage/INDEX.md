# Backstage de mantenimiento

Esta carpeta centraliza material **no eliminado** del repositorio que no forma parte de la cara pública mínima.

## Qué se movió

- `auditorias/`: informes y evidencias de auditoría (MD/JSON) que antes estaban en raíz y `docs/`.
- `docs_historicos/`: readmes duplicados, guías históricas y documentación interna no prioritaria para onboarding público.
- `reportes/`: artefactos generados (resúmenes/calidad/cobertura histórica).
- `launchers_legacy/`: launchers `.bat` redundantes o legacy.
- `scripts_legacy/`: scripts batch legacy/no esenciales para el flujo actual.
- `pocs/`: ejemplos/PoCs no críticos para operación principal.

## Por qué

- Reducir ruido en la raíz y en `docs/`.
- Mantener una cara pública enfocada en uso, arquitectura y soporte.
- Preservar trazabilidad histórica sin borrar activos (`NO DELETE`).

## Cómo restaurar algo

1. Localiza el archivo en `_backstage/`.
2. Muévelo de vuelta a su ubicación deseada (ejemplo con git):

```bash
git mv _backstage/docs_historicos/onboarding.md docs/onboarding.md
```

3. Si restauras documentos públicos, revisa y actualiza enlaces en `README.md` y `docs/`.
