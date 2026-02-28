# Auditoría técnica cuantitativa

- **Fecha:** 2026-02-19 19:59:03
- **Commit:** `19716d8`

## Métricas base

| Métrica | Valor |
|---|---|
| `max_file_lines` | `1877` |
| `max_file_path` | `app/ui/main_window.py` |
| `critical_modules_over_500` | `6` |
| `modules_over_800` | `4` |
| `main_window_lines` | `0` |
| `use_cases_lines` | `0` |
| `coverage_threshold` | `63` |
| `coverage_thresholds_aligned` | `True` |
| `whitelist_active` | `False` |
| `architecture_violations` | `0` |
| `tests_count` | `129` |
| `coverage` | `None` |
| `secrets_outside_repo` | `True` |
| `secret_paths` | `[]` |
| `db_in_repo_root` | `False` |
| `db_paths` | `[]` |
| `has_env_example` | `False` |
| `has_contributing` | `True` |
| `has_changelog` | `True` |
| `has_dod` | `True` |
| `has_roadmap` | `False` |
| `ci_green` | `True` |
| `release_automated` | `True` |
| `correlation_id_implemented` | `True` |
| `structured_logs` | `True` |

## Score por áreas

| Área | Peso | Score (0-100) | Aporte ponderado | Cálculo |
|---|---:|---:|---:|---|
| Arquitectura estructural | 20% | 62 | 12.40 | base 100 - penalties 38 |
| Testing & cobertura | 20% | 0 | 0.00 | base 60 cov=0.00 threshold=63 |
| Complejidad accidental | 15% | 54 | 8.10 | base 100 - penalties 46 |
| DevEx / CI / Governance | 15% | 100 | 15.00 | base 50 + bonuses |
| Observabilidad y resiliencia | 10% | 100 | 10.00 | base 60 + bonuses |
| Configuración & seguridad | 10% | 90 | 9.00 | base 55 + bonuses/penalties |
| Documentación & gobernanza | 10% | 90 | 9.00 | base 20 + bonuses |

## Score global ponderado

**63.50 / 100**

## Plan priorizado (Top 5)

1. **[Testing & cobertura]** Cerrar brecha de 100 puntos (impacto área: +100, impacto global: +20.00).
2. **[Arquitectura estructural]** Cerrar brecha de 38 puntos (impacto área: +38, impacto global: +7.60).
3. **[Complejidad accidental]** Cerrar brecha de 46 puntos (impacto área: +46, impacto global: +6.90).
4. **[Configuración & seguridad]** Cerrar brecha de 10 puntos (impacto área: +10, impacto global: +1.00).
5. **[Documentación & gobernanza]** Cerrar brecha de 10 puntos (impacto área: +10, impacto global: +1.00).

## Evidencias

### Arquitectura
- tests/test_architecture_imports.py:10: ALLOWED_VIOLATIONS: set[tuple[str, str]] = set()
- tests/test_architecture_imports.py:13: "sqlite3",
- tests/test_architecture_imports.py:14: "gspread",
- tests/test_architecture_imports.py:119: "Application no debe importar librerías técnicas específicas (sqlite3/gspread/googleapiclient).",
- tests/test_architecture_imports.py:143: if (record.source_file, record.imported_module) in ALLOWED_VIOLATIONS:
- tests/test_architecture_imports.py:169: forbidden = {"sqlite3", "gspread", "googleapiclient", "google.auth", "google_auth_oauthlib"}
- tests/test_architecture_imports.py:178: assert not violations, "application must not import sqlite3/gspread/google-auth libs:\n" + "\n".join(violations)
- Comando: PYTHONPATH=. pytest -q tests/test_architecture_imports.py
- ..                                                                       [100%]
2 passed in 0.28s

### Complejidad
- `app/ui/main_window.py`: 1877 líneas
- `app/application/use_cases/sync_sheets.py`: 1678 líneas
- `app/application/use_cases/__init__.py`: 1063 líneas
- `app/infrastructure/repos_sqlite.py`: 845 líneas
- `scripts/product_audit.py`: 694 líneas
- `tests/application/test_sheets_sync_summary.py`: 539 líneas
- `app/infrastructure/repos_conflicts_sqlite.py`: 468 líneas
- `app/ui/widgets/toast.py`: 438 líneas
- `app/pdf/pdf_builder.py`: 306 líneas
- `app/ui/person_dialog.py`: 298 líneas

### Seguridad
- No se detectaron secretos en repo root/app
- No se detectaron DB en raíz

### Coverage
- .config/quality_gate.json -> coverage_fail_under=63
- Comando: PYTHONPATH=. pytest -q --cov=app --cov-report=term-missing
- ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] [...]
pytest: error: unrecognized arguments: --cov=app --cov-report=term-missing
  inifile: None
  rootdir: /workspace/Horas_Sindicales

## Tendencia
- Tendencia calculada contra auditoría previa.
- Score global actual vs anterior: 63.50 vs 61.90 (delta: 1.6)
- Top 3 mejoras:
- Arquitectura estructural: +8
- Top 3 regresiones:
- N/A

## Warnings
- ⚠️ No se pudo calcular coverage real porque falta pytest-cov.
