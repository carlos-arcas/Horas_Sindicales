# AUDITORÍA E2E (<ID>)
- Fecha UTC: <FECHA>
- Branch: main
- Commit: abc1234

## Resumen
- Resultado global: **PASS**
- Scorecard: **9.17/10**

## Tabla de checks
| Check | Estado | Severidad | Evidencias |
|---|---|---|---|
| CHECK-ARQ-001 | PASS | ALTO | Sin violaciones de imports UI->infra y domain->externo. |
| CHECK-TEST-001 | NO_EVALUABLE | MEDIO | requirements-dev.txt con pytest=sí; ejecutar_tests.bat con comando estándar=sí; Cobertura dinámica no evaluada en auditoría estática. |
| CHECK-LOG-001 | PASS | ALTO | Sin print en app/main=sí; Rotación configurada=sí; crashes.log configurado=sí |
| CHECK-WIN-001 | PASS | MEDIO | Scripts windows presentes=sí; Requirements pinneados=sí |
| CHECK-DOC-001 | PASS | BAJO | Docs mínimas presentes |
| CHECK-VCS-001 | PASS | MEDIO | VERSION=1.0.0; Entrada en CHANGELOG=sí |

## Backlog recomendado
Sin backlog recomendado.
