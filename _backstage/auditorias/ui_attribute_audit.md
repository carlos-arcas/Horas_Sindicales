# Auditoría de atributos `self.*` en `MainWindow`

## Resumen
- Riesgo **No inicializado**: **0**.
- Los 19 atributos reportados previamente ya tienen inicialización explícita en `MainWindow.__init__` y luego se reasignan en sus builders correspondientes.

## Atributos regularizados
- `_sync_thread`, `_sync_worker`
- `status_sync_label`, `status_sync_progress`, `status_pending_label`
- `saldos_details_button`, `saldos_details_content`
- `saldo_periodo_label`, `saldo_periodo_consumidas`, `saldo_periodo_restantes`
- `saldo_grupo_consumidas`, `saldo_grupo_restantes`
- `saldo_anual_consumidas`, `saldo_anual_restantes`
- `exceso_badge`
- `bolsa_mensual_label`, `bolsa_delegada_label`, `bolsa_grupo_label`
- `horas_input`

## Nota
Este documento refleja el estado posterior al fix **BUG-UI-006**: inicialización obligatoria de atributos UI/Sync para eliminar accesos a atributos no definidos.
