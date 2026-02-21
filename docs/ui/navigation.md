# Navegación UI (MainWindow)

## Inventario previo (problema detectado)

- **Sidebar** coexistía con navegación interna por tabs, generando duplicación de rutas.
- **Tabs internas** existentes en `main_window_vista.py`:
  - Operativa (solicitudes)
  - Histórico
  - Configuración
  - Sincronización
- **QStackedWidget** shell:
  - Página Resumen
  - Página contenedora de tabs (Solicitudes/Histórico/Config/Sync)
- **Acciones repetidas** (múltiples entradas al mismo flujo):
  - Sincronizar ahora (menu y sección sync)
  - Nueva solicitud / limpiar formulario (resumen, header y operativa)
  - Configuración (sidebar y menú)

## Mapa final (mínimo, patrón principal = Sidebar)

Patrón principal elegido: **Sidebar + stacked pages**.

Páginas visibles de navegación principal:
1. **Resumen**
2. **Solicitudes**
3. **Histórico**
4. **Configuración**

## Header global

Acciones globales primarias:
- **Nuevo**
- **Sync**
- **Exportar**
- **Config**

Acciones secundarias:
- Menú **Más** (`QMenu`) con acciones de soporte (salud del sistema, historial de sincronización, acceso rápido a configuración).

## Notas de implementación

- Se mantuvo `MainWindow` como orquestador.
- Se extrajeron builders para simplificar estructura:
  - `_build_shell_layout`
  - `_create_sidebar`
  - `_create_pages_stack`
