# Features pendientes

## FTR-011 - Ejecutar validacion final en Windows real y consolidar evidencia de cierre
- Estado: **BLOCKED**
- Tipo: `INFRA`
- Tests:
  - `tests/test_docs_minimas.py`
  - `tests/test_windows_scripts_contract.py`
  - `tests/test_launcher_bat_contract.py`
  - `tests/test_definicion_producto_final_contract.py`
  - `tests/test_validacion_windows_real_contract.py`
- Notas: Prioridad 6 (cierre real de producto). BLOCKED hasta disponer de arbol limpio o snapshot identificable del commit validado y una sesion Windows real con revision visual/manual de lanzar_app.bat y launcher.bat segun docs/validacion_windows_real.md. En este worktree persisten cambios locales ajenos y el contexto de automatizacion no sustituye esa evidencia manual final.
