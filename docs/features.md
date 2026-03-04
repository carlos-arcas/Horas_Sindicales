# Inventario de features

| ID | Nombre | Estado | Tipo | Tests | Notas |
|---|---|---|---|---|---|
| FTR-001 | Registro y gestión de solicitudes sindicales | DONE | LOGICA | tests/application/test_solicitudes_use_case_calculos.py<br>tests/domain/test_request_duration.py | Cobertura funcional base de solicitudes, validaciones y cálculo de duración. |
| FTR-002 | Sincronización con Google Sheets | WIP | INFRA | tests/application/test_sync_sheets_use_case_scenarios.py<br>tests/application/use_cases/sync_sheets/test_sync_sheets_use_case_planning.py | En evolución continua para robustez de conflictos y reporting. |
| FTR-003 | Golden tests de interacción en botones clave | DONE | UI | tests/golden/botones/test_boton_aniadir_pendiente_golden.py<br>tests/golden/botones/test_boton_sync_golden.py | - |
| FTR-004 | Controles de seguridad y secretos en repo | DONE | SEGURIDAD | tests/test_no_secrets_content_scan.py | - |
| FTR-005 | Vertical slice de personajes (stack Django en transición) | WIP | UI | tests/application/personajes/test_casos_uso_personajes.py<br>tests/domain/personajes/test_servicios_personaje.py<br>tests/web/test_personajes.py | Porting incremental con strangler, pendiente integración completa de Django runtime. |
