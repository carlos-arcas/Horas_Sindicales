# Auditoría técnica cuantitativa

- **Fecha:** 2026-02-19 19:47:59
- **Commit:** `6ecc0fb`

## Métricas base

| Métrica | Valor |
|---|---|
| `coverage` | `64.59` |
| `max_file_lines` | `907` |
| `main_window_lines` | `0` |
| `use_cases_lines` | `488` |
| `architecture_violations` | `1` |
| `ci_green` | `True` |
| `release_automated` | `True` |
| `whitelist_active` | `True` |
| `tests_count` | `119` |
| `critical_modules_over_500` | `3` |
| `coverage_thresholds_aligned` | `True` |
| `correlation_id_implemented` | `True` |
| `structured_logs` | `True` |
| `secrets_outside_repo` | `True` |
| `db_in_repo_root` | `True` |
| `has_contributing` | `True` |
| `has_changelog` | `True` |
| `has_dod` | `True` |
| `has_roadmap` | `False` |

## Score por áreas

| Área | Peso | Score (0-100) | Aporte ponderado | Cálculo |
|---|---:|---:|---:|---|
| Arquitectura estructural | 20% | 65 | 13.00 | 100 - (3*5) - (1*10) - 10 whitelist |
| Testing & cobertura | 20% | 52 | 10.40 | 50 base ; +(64.59-60)*1.5=6.89 ; -10 por coverage < 65 ; +5 por tests_count > 100 |
| Complejidad accidental | 15% | 82 | 12.30 | 100 - round(907/100) - (3*3) |
| DevEx / CI / Governance | 15% | 70 | 10.50 | +40 CI en verde ; +20 release automatizado ; +10 thresholds alineados |
| Observabilidad y resiliencia | 10% | 50 | 5.00 | +30 correlation_id ; +20 logs estructurados |
| Configuración & seguridad | 10% | 40 | 4.00 | +50 secretos fuera del repo ; -10 DB en raíz |
| Documentación & gobernanza | 10% | 80 | 8.00 | +40 CONTRIBUTING ; +20 CHANGELOG ; +20 DoD formal |

## Score global ponderado

**63.20 / 100**

## Brechas para llegar a 100

- **Arquitectura estructural**: faltan 35 puntos para llegar a 100.
- **Testing & cobertura**: faltan 48 puntos para llegar a 100.
- **Complejidad accidental**: faltan 18 puntos para llegar a 100.
- **DevEx / CI / Governance**: faltan 30 puntos para llegar a 100.
- **Observabilidad y resiliencia**: faltan 50 puntos para llegar a 100.
- **Configuración & seguridad**: faltan 60 puntos para llegar a 100.
- **Documentación & gobernanza**: faltan 20 puntos para llegar a 100.

## Plan priorizado (Top 5)

1. **[Testing & cobertura]** Incrementar cobertura para acercarse al score máximo del área (impacto área: +43, impacto global: +8.60).
2. **[Arquitectura estructural]** Reducir módulos críticos (>500 líneas) de 3 a 0 (impacto área: +15, impacto global: +3.00).
3. **[Arquitectura estructural]** Eliminar violaciones de capa (actuales: 1) (impacto área: +10, impacto global: +2.00).
4. **[Arquitectura estructural]** Remover whitelist activa en tests de arquitectura (impacto área: +10, impacto global: +2.00).
5. **[Testing & cobertura]** Subir cobertura al menos a 65% (impacto área: +10, impacto global: +2.00).
