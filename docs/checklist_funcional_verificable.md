# Checklist funcional verificable

Este documento define el mapa funcional base del producto para auditar el estado real función por función.

Regla editorial aplicada: cuando no hay evidencia sólida, el estado queda en **No verificada**.

## Escala de estados

- **Verificada**
- **Parcial**
- **No verificada**
- **No implementada**

## Inventario funcional

### FUN-001 — Lanzar la aplicación desde entrypoints oficiales
- **Descripción humana:** Se puede lanzar la aplicación desde los entrypoints oficiales de Windows.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test + documentación.
- **Fuentes de evidencia:** `tests/test_launcher_bat_contract.py`, `docs/definicion_producto_final.md`.
- **Observaciones/bloqueos:** Existe contrato de launcher y entrypoints, pero no hay evidencia automatizada de ejecución real en Windows dentro de la suite actual.

### FUN-002 — Completar arranque y llegar a ventana principal
- **Descripción humana:** Se puede completar el arranque (splash/boot) y llegar a una ventana principal operativa.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test + documentación.
- **Fuentes de evidencia:** `tests/ui/test_ui_arranque_minimo.py`, `tests/test_main_window_wiring_contract.py`, `tests/entrypoints/test_receptor_arranque.py`, `docs/ui/arranque_ui_regresion_wiring_hilos.md`.
- **Observaciones/bloqueos:** Hay smoke y contratos de arranque; no hay prueba E2E de interfaz completa con splash real en Windows.

### FUN-003 — Seleccionar delegada
- **Descripción humana:** Se puede seleccionar una delegada activa en el flujo de trabajo.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test + flujo manual documentado.
- **Fuentes de evidencia:** `tests/ui_rules/test_personas_presenter.py`, `docs/ui/navigation.md`.
- **Observaciones/bloqueos:** La selección y resolución están cubiertas a nivel presenter; no hay E2E UI completo con interacción real de combo/lista.

### FUN-004 — Rellenar fecha y horas de solicitud
- **Descripción humana:** Se puede rellenar fecha y horas para preparar una solicitud.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/ui/test_confirmar_pdf_flow.py`, `tests/application/solicitudes/test_validacion_basica.py`, `tests/test_solicitudes_controller_helpers.py`.
- **Observaciones/bloqueos:** Hay contratos de campos y validaciones, pero falta evidencia integral del formulario completo en una sola prueba E2E UI.

### FUN-005 — Ver saldo reservado actualizado
- **Descripción humana:** Se puede ver el saldo reservado actualizado al operar con pendientes.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/presentacion/test_reservado_refresh_contract.py`, `tests/application/solicitudes/test_saldos_service.py`.
- **Observaciones/bloqueos:** Hay contratos de recálculo y refresco; no hay evidencia E2E de pantalla completa con datos reales de usuario.

### FUN-006 — Añadir pendiente
- **Descripción humana:** Se puede añadir una solicitud como pendiente.
- **Prioridad:** Alta.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/presentacion/test_agregar_pendiente_contract.py`, `tests/golden/botones/test_boton_aniadir_pendiente_golden.py`, `tests/integration/test_confirmacion_pendientes_pdf_sqlite.py`, `tests/e2e/test_flujo_solicitud_pdf_historico.py`.
- **Observaciones/bloqueos:** El contrato de presentación cubre alta de pendiente, refresco de cajón/totales/saldo/estado y validación controlada sin excepción; además se mantiene evidencia golden e integración del flujo completo.

### FUN-007 — Seleccionar pendiente
- **Descripción humana:** Se puede seleccionar pendientes para operar sobre ellos.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/ui/test_confirmar_pdf_flow.py`, `tests/ui/test_pendientes_confirmar_layout.py`, `tests/ui_rules/test_pending_duplicate_presenter.py`.
- **Observaciones/bloqueos:** Se valida selección y reglas de conflictos/duplicados en contratos; no hay evidencia E2E UI de selección múltiple con render real.

### FUN-008 — Confirmar pendiente y generar PDF
- **Descripción humana:** Se puede confirmar una solicitud pendiente y generar PDF.
- **Prioridad:** Alta.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/application/test_confirmar_pdf_caso_uso.py`, `tests/integration/test_confirmacion_pendientes_pdf_sqlite.py`, `tests/e2e/test_confirmacion_pdf_e2e.py`, `tests/e2e/test_flujo_solicitud_pdf_historico.py`.
- **Observaciones/bloqueos:** La lógica y el E2E de confirmación+PDF están cubiertos; la verificación UI completa queda parcial por uso de contratos headless.

### FUN-009 — Elegir ruta de guardado
- **Descripción humana:** Se puede elegir ruta de guardado para el PDF de confirmación.
- **Prioridad:** Alta.
- **Estado global:** Parcial.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/presentacion/test_handlers_prioridad1_contract.py`, `tests/presentacion/test_confirm_prompt_contract.py`.
- **Observaciones/bloqueos:** Existe contrato del prompt y manejo de colisiones; no hay evidencia E2E de diálogo nativo en SO real.

### FUN-010 — Guardar PDF en disco
- **Descripción humana:** Se puede guardar el PDF generado en disco con salida válida.
- **Prioridad:** Alta.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/integration/test_confirmacion_pendientes_pdf_sqlite.py`, `tests/e2e/test_flujo_solicitud_pdf_historico.py`, `tests/e2e/test_exportacion_pdf_historico_e2e.py`.
- **Observaciones/bloqueos:** La persistencia de PDF está verificada por integración y E2E; la interacción de selector de archivos queda en contratos.

### FUN-011 — Consultar histórico de solicitudes confirmadas
- **Descripción humana:** Se puede consultar el histórico de solicitudes confirmadas.
- **Prioridad:** Alta.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/application/test_solicitudes_historico_use_case.py`, `tests/e2e/test_flujo_solicitud_pdf_historico.py`, `tests/ui/test_historico_view_smoke.py`.
- **Observaciones/bloqueos:** El histórico queda cubierto en caso de uso y E2E de flujo prioritario; filtros y UX avanzada se validan en contratos adicionales.

### FUN-012 — Abrir PDF automáticamente con toggle activado
- **Descripción humana:** Se puede abrir automáticamente el PDF generado si el toggle correspondiente está activado.
- **Prioridad:** Media.
- **Estado global:** No verificada.
- **Evidencia actual:** ninguna.
- **Fuentes de evidencia:** ninguna.
- **Observaciones/bloqueos:** No se encontró prueba explícita de este comportamiento en los tests inspeccionados del repositorio.

### FUN-013 — Preflight de escritura en sincronización
- **Descripción humana:** Se puede ejecutar preflight de escritura para sincronización y detectar falta de permisos/configuración.
- **Prioridad:** Media.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/infrastructure/test_sheets_client_write_preflight.py`, `tests/application/test_sync_preflight_permissions.py`.
- **Observaciones/bloqueos:** Cobertura fuerte de infraestructura y aplicación; la UI de este flujo no es foco del ciclo.

### FUN-014 — Contrato de botones críticos
- **Descripción humana:** Se mantienen contratos de botones críticos para evitar regresiones de wiring en ventana principal.
- **Prioridad:** Media.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/presentacion/test_contrato_botones.py`, `tests/golden/botones/test_boton_sync_golden.py`.
- **Observaciones/bloqueos:** Contrato y golden cubren wiring crítico de botones.

### FUN-015 — Contrato de señales
- **Descripción humana:** Se mantienen contratos de señales y adaptadores para evitar errores de conexión de eventos UI.
- **Prioridad:** Media.
- **Estado global:** Verificada.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/presentacion/test_contrato_senales.py`, `docs/contrato_wiring.md`.
- **Observaciones/bloqueos:** La capa de señales queda protegida por contratos unitarios explícitos.

### FUN-016 — Toasts con contrato estable
- **Descripción humana:** Se notifican resultados y errores mediante toasts con contrato estable.
- **Prioridad:** Media.
- **Estado global:** Parcial.
- **Evidencia actual:** test.
- **Fuentes de evidencia:** `tests/aplicacion/notificaciones/test_dto_toast.py`, `tests/ui/test_toast_signal_smoke_contract.py`, `tests/test_toast_manager_actions.py`.
- **Observaciones/bloqueos:** Hay cobertura amplia de contrato de notificación, sin E2E UI completo.

## Ruta crítica inicial (flujo prioritario)

1. **FUN-001** — lanzar app.
2. **FUN-002** — pasar arranque y entrar en ventana principal.
3. **FUN-003** — seleccionar delegada.
4. **FUN-004** — rellenar fecha/horas.
5. **FUN-005** — ver saldo reservado actualizado.
6. **FUN-006** — añadir pendiente.
7. **FUN-007** — seleccionar pendiente.
8. **FUN-008** — confirmar y generar PDF.
9. **FUN-009** — elegir ruta de guardado.
10. **FUN-010** — guardar PDF.
11. **FUN-011** — comprobar aparición en histórico.
12. **FUN-012** — abrir PDF si toggle está activado.
