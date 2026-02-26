# Navegación UI (MainWindow)

## Mapa actual (mínimo)

Patrón principal: **Sidebar + páginas internas**.

Secciones visibles:
1. **Solicitudes**
2. **Histórico**
3. **Configuración**

La pestaña **Sincronización** se mantiene dentro del contenido de Solicitudes (tabs internas ocultas por la navegación lateral).

## Cabecera global

La cabecera global fue eliminada para reducir ruido visual y evitar acciones duplicadas.

Acciones reubicadas:
- **Nueva solicitud**: botón en sección de Solicitudes (junto a la selección de delegada).
- **Sincronizar ahora**: botones en pestaña Sincronización.
- **Exportar histórico PDF**: botón en pestaña Histórico.
- **Config**: acceso por navegación lateral a Configuración.
- **Más / selector de contexto**: retirados del shell.

## Notas de implementación

- `MainWindow` mantiene rol de orquestación UI sin mover lógica de negocio.
- Se simplificó `_build_shell_layout` eliminando dependencias de header.
- Se actualizaron tests de contrato UI para verificar que el header no existe y que las acciones siguen disponibles en sus páginas.
