# Bitacora Codex

> Registro operativo derivado de la ejecucion del agente.
> No sustituye `docs/features.json` ni redefine estados funcionales.

## 2026-03-26 - FTR-006

- Tarea ejecutada: `FTR-006 - Corregir fallo reproducible del gate rapido en entorno local`
- Alcance aplicado:
  - resolver el arranque de gates contra el Python del repo;
  - blindar `gate_rapido` para subruns core sin `pytest-qt`;
  - corregir la normalizacion de rutas en auditoria E2E detectada por tests de aplicacion.
- Archivos modificados:
  - `docs/roadmap_codex.md`
  - `docs/bitacora_codex.md`
  - `scripts/runtime_python.py`
  - `scripts/gate_rapido.py`
  - `scripts/gate_pr.py`
  - `app/application/auditoria_e2e/reglas.py`
  - `tests/tools/test_gate_rapido.py`
  - `tests/tools/test_gate_pr.py`
  - `tests/tools/test_runtime_python.py`
- Decisiones tecnicas tomadas:
  - priorizar `.venv` como interprete de ejecucion de gates para no depender del Python global;
  - reutilizar el harness `core-no-ui` ya existente en `app.testing.qt_harness`;
  - mantener el roadmap y la bitacora como vistas operativas, no como fuente paralela de verdad.
- Validaciones ejecutadas y resultado:
  - `python -m scripts.gate_rapido` antes del fix: FAIL por `No module named ruff`
  - `python -m scripts.gate_pr` antes del fix: FAIL al validar `pytest --help` en el interprete global
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\gate_rapido.py scripts\\gate_pr.py scripts\\runtime_python.py tests\\tools\\test_gate_rapido.py tests\\tools\\test_gate_pr.py tests\\tools\\test_runtime_python.py app\\application\\auditoria_e2e\\reglas.py`: PASS
  - `.\\.venv\\Scripts\\python.exe -m pytest -q -p no:pytestqt -p no:pytestqt.plugin tests\\tools\\test_gate_rapido.py tests\\tools\\test_gate_pr.py tests\\tools\\test_runtime_python.py tests\\application\\test_auditoria_e2e_reglas_arquitectura.py`: PASS
  - `python -m scripts.gate_rapido` despues del fix: BLOQUEADO por `PermissionError [WinError 5]` en `C:\\Users\\arcas\\AppData\\Local\\Temp\\pytest-of-arcas`
  - `python -m scripts.gate_pr` despues del fix: BLOQUEADO/NO VERIFICABLE por el mismo problema y por directorios temporales inaccesibles generados por `pytest`
- Errores detectados y correccion aplicada:
  - error de arranque por `ruff` ausente en el Python global: corregido usando `.venv` cuando existe;
  - subrun core de `gate_rapido` sin harness no-UI: corregido reutilizando `qt_harness`;
  - evidencia con separadores Windows en auditoria E2E: corregida a POSIX.
- Bloqueos actuales:
  - `pytest` deja directorios temporales inaccesibles para el propio proceso Python en este entorno (`PermissionError [WinError 5]`);
  - esos residuos temporales impiden cerrar `gate_rapido` y contaminan `gate_pr`/`git status`.
- Siguiente paso recomendado:
  - limpiar o recuperar permisos de los directorios temporales inaccesibles desde el entorno Windows anfitrion;
  - reintentar `python -m scripts.gate_rapido`;
  - si pasa, ejecutar `python -m scripts.gate_pr`.
