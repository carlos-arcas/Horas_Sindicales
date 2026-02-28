# Inventario de limpieza del repositorio

> Objetivo: dejar una cara pública mínima sin borrar archivos. Todo elemento marcado como `MOVE_BACKSTAGE` se moverá a `_backstage/` en la fase 2.

## Árbol público final propuesto

- `README.md` (único, limpio)
- `docs/README_tecnico.md`
- `docs/DECISIONES_TECNICAS.md`
- `docs/SOPORTE.md`
- `app/`
- `tests/`
- `scripts/` (solo scripts de desarrollo/CI activos)
- `packaging/` e `installer/` (build/distribución)
- `.github/workflows/`, `requirements*.txt|.in`, `Makefile`, `ruff.toml`, `migrations/`, `.config/`

## Tabla de inventario

| path actual | tipo | acción | motivo | EJECUTADO |
|---|---|---|---|---|
| `README.md` | DOC_PUBLICA | KEEP_PUBLIC | README principal del proyecto. | sí |
| `docs/decisiones_tecnicas.md` | DOC_PUBLICA | KEEP_PUBLIC | Base para `docs/DECISIONES_TECNICAS.md`. | sí |
| `docs/onboarding.md` | DOC_INTERNA | MOVE_BACKSTAGE | Onboarding interno; se consolidará en técnico/soporte. | sí |
| `docs/arquitectura.md` | DOC_PUBLICA | KEEP_PUBLIC | Insumo de arquitectura para decisiones técnicas. | sí |
| `docs/sincronizacion_google_sheets.md` | DOC_PUBLICA | KEEP_PUBLIC | Fuente para sección de sync en docs públicos. | sí |
| `docs/guia_pruebas.md` | DOC_PUBLICA | KEEP_DEV | Referencia útil para desarrollo y QA. | sí |
| `docs/release_windows.md` | DOC_INTERNA | KEEP_DEV | Documentación de empaquetado/release para maintainers. | sí |
| `docs/release_process.md` | DOC_INTERNA | KEEP_DEV | Proceso de release para equipo técnico. | sí |
| `docs/quality_gate.md` | DOC_INTERNA | KEEP_DEV | Contrato de calidad de CI/desarrollo. | sí |
| `docs/coverage_policy.md` | DOC_INTERNA | KEEP_DEV | Política de cobertura usada por CI. | sí |
| `docs/coverage_scope.md` | DOC_INTERNA | KEEP_DEV | Alcance de cobertura para validaciones. | sí |
| `docs/guia_cobertura.md` | DOC_INTERNA | KEEP_DEV | Guía de cobertura para desarrollo. | sí |
| `docs/guia_pruebas_coverage_plan.md` | DOC_INTERNA | MOVE_BACKSTAGE | Plan histórico redundante de pruebas/cobertura. | sí |
| `docs/guia_logging.md` | DOC_INTERNA | KEEP_DEV | Operación/diagnóstico para dev soporte. | sí |
| `docs/docs_style_guide.md` | DOC_INTERNA | KEEP_DEV | Convenciones editoriales internas. | sí |
| `docs/convenciones_naming.md` | DOC_INTERNA | KEEP_DEV | Convenciones técnicas activas. | sí |
| `docs/base_datos_local.md` | DOC_PUBLICA | KEEP_DEV | Referencia de SQLite local para dev/soporte. | sí |
| `docs/api_sync_module.md` | DOC_PUBLICA | KEEP_DEV | API técnica del módulo sync para dev. | sí |
| `docs/menu_validacion.md` | DOC_INTERNA | MOVE_BACKSTAGE | Guía ligada a launcher legacy de validación. | sí |
| `docs/roadmap_senior.md` | DOC_INTERNA | MOVE_BACKSTAGE | Documento estratégico/histórico no esencial público. | sí |
| `docs/definicion_producto_final.md` | DOC_INTERNA | KEEP_DEV | Documento contractual requerido por tests; versión histórica también en `_backstage/docs_historicos/`. | sí |
| `docs/definition_of_done.md` | DOC_INTERNA | MOVE_BACKSTAGE | Checklist interno, no parte de cara pública. | sí |
| `docs/ui_attribute_audit.md` | AUDITORIA | MOVE_BACKSTAGE | Evidencia de auditoría puntual de UI. | sí |
| `docs/audits/2026-02-19_1959_19716d8.json` | AUDITORIA | MOVE_BACKSTAGE | Artefacto de auditoría fechado. | sí |
| `docs/AUDITORIA_UX_v1.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría UX. | sí |
| `docs/auditoria_producto.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría. | sí |
| `docs/auditoria_portfolio.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría. | sí |
| `docs/auditoria_v7.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría versión histórica. | sí |
| `docs/auditoria_senior.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría. | sí |
| `docs/auditoria_general.md` | AUDITORIA | MOVE_BACKSTAGE | Informe de auditoría general histórica. | sí |
| `docs/quality_gate_evidencia.md` | AUDITORIA | MOVE_BACKSTAGE | Evidencia puntual de ejecución quality gate. | sí |
| `docs/CHANGELOG.md` | DOC_INTERNA | MOVE_BACKSTAGE | Changelog duplicado; canonical en raíz. | sí |
| `CHANGELOG.md` | DOC_PUBLICA | KEEP_PUBLIC | Changelog canonical del repositorio. | sí |
| `AUDITORIA.md` | AUDITORIA | KEEP_DEV | Stub contractual en raíz; original histórico también en `_backstage/auditorias/`. | sí |
| `auditoria.json` | AUDITORIA | KEEP_DEV | Stub contractual en raíz; original histórico también en `_backstage/auditorias/`. | sí |
| `README_DECISIONES_TECNICAS.md` | DOC_INTERNA | MOVE_BACKSTAGE | README duplicado de decisiones técnicas. | sí |
| `README_TUTORIAL.md` | DOC_INTERNA | MOVE_BACKSTAGE | Tutorial histórico fuera de docs públicos objetivo. | sí |
| `arquitectura.md` | DOC_INTERNA | MOVE_BACKSTAGE | Duplicado raíz de arquitectura (canonical en docs). | sí |
| `CONTRIBUTING.md` | DOC_INTERNA | KEEP_DEV | Guía de contribución para maintainers. | sí |
| `logs/README.md` | DOC_INTERNA | MOVE_BACKSTAGE | README de carpeta de evidencias/logs no pública. | sí |
| `logs/summary.txt` | REPORTE | MOVE_BACKSTAGE | Reporte generado, no fuente del proyecto. | sí |
| `logs/quality_report.txt` | REPORTE | MOVE_BACKSTAGE | Evidencia generada del quality gate. | sí |
| `examples/sync_module_example.py` | POC | MOVE_BACKSTAGE | Ejemplo auxiliar no esencial para usuario final. | sí |
| `lanzar_app.bat` | LAUNCHER | KEEP_DEV | Requerido por contratos de tests; copia legacy preservada en `_backstage/launchers_legacy/`. | sí |
| `launch.bat` | LAUNCHER | MOVE_BACKSTAGE | Launcher legacy redundante. | sí |
| `launcher.bat` | LAUNCHER | KEEP_DEV | Requerido por contratos de tests; copia legacy preservada en `_backstage/launchers_legacy/`. | sí |
| `auditar_e2e.bat` | SCRIPT_DEV | KEEP_DEV | Requerido por flujo/batería contractual; copia legacy en `_backstage/scripts_legacy/`. | sí |
| `menu_validacion.bat` | SCRIPT_DEV | KEEP_DEV | Requerido por contratos automatizados; variante histórica movida a `_backstage/scripts_legacy/`. | sí |
| `quality_gate.bat` | SCRIPT_DEV | KEEP_DEV | Requerido por contratos de calidad; copia histórica en `_backstage/scripts_legacy/`. | sí |
| `ejecutar_tests.bat` | SCRIPT_DEV | KEEP_DEV | Requerido por contratos de tests; copia histórica en `_backstage/scripts_legacy/`. | sí |
| `scripts/menu_validacion.bat` | SCRIPT_LEGACY | MOVE_BACKSTAGE | Launcher BAT legacy de validación. | sí |
| `scripts/bat/` | SCRIPT_LEGACY | MOVE_BACKSTAGE | Scripts BAT dummy/legacy para validación histórica. | sí |
| `scripts/release/*.bat` | SCRIPT_LEGACY | MOVE_BACKSTAGE | Batch legacy; se mantiene `release.py` para flujo dev. | sí |
| `scripts/release/release.py` | SCRIPT_DEV | KEEP_DEV | Script activo de automatización de release. | sí |
| `installer/HorasSindicales.iss` | OTRO | KEEP_DEV | Definición installer (aplica a packaging). | sí |
| `packaging/HorasSindicales.spec` | OTRO | KEEP_DEV | Especificación de empaquetado PyInstaller. | sí |
| `tests/expanded/README.md` | DOC_INTERNA | MOVE_BACKSTAGE | README auxiliar de pruebas expandidas históricas. | sí |
| `tests/expanded/COVERAGE_REPORT.md` | REPORTE | MOVE_BACKSTAGE | Reporte de cobertura histórico. | sí |
