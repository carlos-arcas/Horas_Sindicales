# Cierre final de readonly

## Estado final

**Resultado:** PASS condicionado a validación manual pendiente en Windows real.

La feature `readonly` puede declararse **CERRADA** en el código versionado porque el backend mutante relevante, la UI preventiva, el contrato compartido y los guardarraíles estructurales tienen evidencia automatizada en el repositorio. La única validación no ejecutada en esta auditoría Linux es la comprobación manual final en Windows real, requerida por la política general del producto.

## Alcance auditado

Readonly cubre mutaciones reales del producto en estas superficies:

### Backend / casos de uso mutantes protegidos

- `app/application/use_cases/solicitudes/use_case.py`
- `app/application/use_cases/solicitudes/crear_pendiente_caso_uso.py`
- `app/application/use_cases/personas/use_case.py`
- `app/application/use_cases/confirmacion_pdf/caso_uso.py`
- `app/application/use_cases/grupos_config/use_case.py`
- `app/application/use_cases/cargar_datos_demo_caso_uso.py`
- `app/application/use_cases/exportar_compartir_periodo.py`

### Owners auditados como no mutantes

- `app/application/use_cases/alert_engine.py`
- `app/application/use_cases/health_check.py`
- `app/application/use_cases/retry_sync_use_case.py`

### Caso dudoso documentado

- `app/application/use_cases/validacion_preventiva_lock_use_case.py`
  - Justificación: ejecuta callbacks potencialmente mutantes, pero no define ni posee la mutación de negocio; solo clasifica errores de lock.

## Fuente única de verdad del contrato readonly

### Estado compartido

- `app/application/modo_solo_lectura.py`
  - `EstadoModoSoloLectura` es la abstracción compartida entre aplicación y UI.

### Política backend

- `app/application/use_cases/politica_modo_solo_lectura.py`
  - `PoliticaModoSoloLectura.verificar()` bloquea mutaciones con el mensaje canónico `Modo solo lectura activado`.

### Política UI e inventario mutante

- `app/ui/vistas/main_window/politica_solo_lectura.py`
  - `ACCIONES_MUTANTES_AUDITADAS_UI`
  - `aplicar_politica_solo_lectura(...)`
  - `resolver_control_mutante(...)`
  - `exportar_inventario_acciones_mutantes(...)`

## Acciones UI auditadas

Las acciones visibles que deben quedar deshabilitadas y con tooltip consistente en modo readonly son:

- `agregar_button`
- `insertar_sin_pdf_button`
- `confirmar_button`
- `eliminar_pendiente_button`
- `eliminar_huerfana_button`
- `add_persona_button`
- `edit_persona_button`
- `delete_persona_button`
- `edit_grupo_button`
- `editar_pdf_button`
- `opciones_button`
- `config_sync_button`
- `sync_button`
- `confirm_sync_button`
- `retry_failed_button`
- `accion_menu_cargar_demo`
- `eliminar_button`
- `generar_pdf_button`

## Evidencias automatizadas

### Backend

- `tests/application/test_read_only_mode.py`
  - Verifica bloqueo funcional y ausencia de side effects en solicitudes, personas y operaciones principales.
- `tests/application/test_exportar_compartir_periodo_caso_uso.py`
  - Verifica bloqueo de exportación persistente en readonly.
- `tests/application/use_cases/grupos_config/test_use_case.py`
  - Verifica bloqueo de configuración de grupo en readonly.
- `tests/application/use_cases/test_cargar_datos_demo_caso_uso.py`
  - Verifica bloqueo de carga demo en readonly.
- `tests/application/test_read_only_inventory_guardrails.py`
  - Verifica que el inventario repo-wide de owners mutantes protegidos se mantenga estable.
- `tests/application/test_read_only_policy_guardrails.py`
  - Verifica contrato de mensaje canónico, inyección obligatoria y ausencia de estado global mutable.

### UI headless / estructural

- `tests/presentacion_pura/main_window/test_read_only_ui_state_headless.py`
  - Verifica deshabilitado, tooltip, fuente única e identidad objectName sin fallback por atributo.
- `tests/presentacion_pura/main_window/test_read_only_ui_guardrails_headless.py`
  - Verifica AST/guardarraíles contra fallback silencioso, drift de inventario y checks manuales fuera del módulo dedicado.
- `tests/presentacion_pura/main_window/test_read_only_ui_inventory_contract.py`
  - Verifica coherencia entre inventario runtime y contrato auditado.

### UI real / smoke mínimo

- `tests/ui/test_read_only_ui_object_names_contract.py`
  - Verifica en Qt real que los controles auditados resuelven por `objectName` y que readonly deshabilita los mismos controles.

### Gate y documentación

- `python -m scripts.gate_pr`
  - Gate canónico completo del proyecto.
- `tests/test_readonly_done_checklist_contract.py`
  - Verifica que esta evidencia de cierre exista y se mantenga alineada con el inventario backend/UI auditado.

## Auditoría final contra criterio de done

### 1) Backend blindado

**PASS**. Los mutantes relevantes auditados están protegidos por la política común y el inventario repo-wide tiene guardarraíl automatizado.

### 2) UI preventiva cerrada

**PASS**. Las acciones mutantes visibles auditadas quedan deshabilitadas, con tooltip consistente, identidad estable por `objectName` y sin fallback silencioso.

### 3) Contrato estable

**PASS**. Existe una fuente compartida para el estado (`EstadoModoSoloLectura`) y una fuente única UI para el inventario mutante (`ACCIONES_MUTANTES_AUDITADAS_UI`).

### 4) Tests suficientes

**PASS**. Hay tests funcionales backend, tests headless UI, smoke mínimo Qt real, guardarraíles AST/estructurales y el gate canónico del proyecto.

### 5) Sin deuda estructural evidente

**PASS**. La auditoría vigente no detecta wrappers legacy activos, fallback por atributo, lógica de test contaminando runtime, estado global mutable ni duplicación fuerte del contrato readonly.

### 6) Evidencia de cierre

**WARNING**. La evidencia documental y automatizada queda cerrada en el repositorio, pero la validación manual en Windows real sigue siendo una comprobación operativa pendiente antes de aprobar producto final completo.

## Validación manual requerida en Windows real

Ejecutar y registrar evidencia de:

1. `lanzar_app.bat`
2. `ejecutar_tests.bat`
3. `python -m pytest -q tests/ui/test_read_only_ui_object_names_contract.py`
4. `python -m scripts.gate_pr`

Comprobaciones manuales mínimas:

- Activar `READ_ONLY=1` y abrir la app.
- Verificar que las acciones mutantes auditadas están deshabilitadas.
- Verificar que muestran el tooltip `ui.read_only.tooltip_mutacion_bloqueada` traducido.
- Verificar que no hay acciones mutantes ejecutables desde menú o botones auditados.
- Guardar evidencia del resultado en la revisión de cierre.

## Decisión de congelación

No se abren nuevas extensiones de readonly salvo que aparezca una mutación real nueva en auditoría funcional futura. A partir de este punto, readonly queda en modo mantenimiento/regresión, no en modo diseño.
