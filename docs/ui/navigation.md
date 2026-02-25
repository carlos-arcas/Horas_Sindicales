# Navegación UI (MainWindow)

## Inventario previo (problema detectado)

- **Sidebar** coexistía con una **cabecera global** con accesos rápidos duplicados.
- **Tabs internas** en `main_window_vista.py`:
  - Operativa (solicitudes)
  - Histórico
  - Configuración
  - Sincronización
- **QStackedWidget** shell:
  - Página Resumen
  - Página contenedora de tabs
- **Duplicaciones de acciones**:
  - Sync (cabecera + sincronización)
  - Exportar (cabecera + histórico)
  - Nueva solicitud (cabecera + resumen/operativa)
  - Config (cabecera + navegación)

## Mapa final (mínimo, patrón principal = Sidebar)

Patrón principal: **Sidebar + stacked pages**.

Páginas visibles de navegación principal:
1. **Resumen**
2. **Solicitudes**
3. **Histórico**
4. **Configuración**

## Sin cabecera global

La cabecera global se eliminó para reducir ruido visual y evitar acciones redundantes.

Acciones reubicadas:
- **Nueva solicitud**: en **Solicitudes/Operativa**.
- **Sincronizar ahora**: en **Sincronización**.
- **Exportar histórico PDF**: en **Histórico**.
- **Configurar**: solo desde **Sidebar > Configuración**.

## Notas de implementación

- `MainWindow` se mantiene como orquestador UI.
- Se conserva separación entre UI y casos de uso (Clean Architecture).
- Se retiraron señales y handlers exclusivos de cabecera para evitar código muerto.
