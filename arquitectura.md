# Arquitectura de `Horas_Sindicales`

> Documento de contexto global. Complementos:
> - decisiones: [docs/decisiones.md](./docs/decisiones.md)
> - reglas funcionales: [docs/reglas_negocio.md](./docs/reglas_negocio.md)
> - sincronización: [docs/sincronizacion_google_sheets.md](./docs/sincronizacion_google_sheets.md)

## 1) Vista por capas

```text
UI (PySide6)                app/ui/*
        │
        ▼
Application (casos de uso)  app/application/* + app/pdf/*
        │
        ▼
Domain (modelo y reglas)    app/domain/*
        ▲
        │ implementaciones concretas
Infrastructure              app/infrastructure/*
```

Composición en runtime: `main.py` crea infraestructura concreta y la inyecta en application/UI.

## 2) Responsabilidades

### Domain
- Entidades y value objects.
- Reglas de negocio y validaciones.
- Puertos (`Protocol`) para repositorios/servicios externos.

Propiedad clave: no depende de PySide, SQLite ni gspread.

### Application
- Orquesta casos de uso.
- Traduce DTOs ↔ entidades.
- Invoca puertos de dominio.

Nota: hay concesiones pragmáticas (por ejemplo, `ConflictsService` usa SQL/SQLite directamente).

### Infrastructure
- Implementa persistencia SQLite (DB, migraciones, repositorios).
- Implementa integración Google Sheets (cliente, repositorio de hojas, sync).
- Gestiona configuración local (`device_id`, credenciales).

### UI
- Presentación e interacción de usuario.
- Conecta acciones de interfaz con casos de uso.
- Ejecuta sincronización en hilos Qt para no bloquear la UI.

## 3) Regla de dependencias
Regla objetivo: `UI -> Application -> Domain`; `Infrastructure` implementa contratos hacia dentro.

Estado real:
- Se cumple en la mayor parte del código.
- No es Clean Architecture estricta por acoplamientos puntuales (SQL en aplicación y módulo `app/pdf` transversal).

## 4) Inyección de dependencias
Patrón: **composition root manual en `main._run_app()`**.

Flujo:
1. conexión SQLite + migraciones/seed,
2. repositorios concretos,
3. servicios/casos de uso,
4. adaptadores de Google Sheets,
5. inyección en `MainWindow`.

No se usa contenedor DI externo.

## 5) Persistencia y sincronización

### SQLite (local, offline-first)
- Fuente operativa local.
- Migraciones al arranque.
- Tablas de negocio y tablas de sincronización (`sync_state`, `conflicts`, etc.).

### Google Sheets (intercambio compartido)
- Backend de sincronización, no fuente inmediata única.
- Esquema de hojas gestionado por código.
- `pull/push/sync` con deduplicación y gestión de conflictos.

## 6) Concurrencia en UI
`MainWindow` usa `QThread` + workers (`SyncWorker`, `PushWorker`) y señales (`finished`, `failed`) para operaciones de red/sync en segundo plano.

## 7) Mejoras prioritarias
1. Extraer `ConflictsService` a puerto + adaptador.
2. Dividir `SheetsSyncService` por submódulos (solicitudes, cuadrantes, config, etc.).
3. Ubicar explícitamente PDF como adaptador de salida.
4. Mejorar observabilidad de sync (métricas por fase).
5. Añadir tests end-to-end de sincronización con DB temporal y dobles de Sheets.

## Resumen
Arquitectura por capas con enfoque pragmático: suficientemente desacoplada para evolucionar, con decisiones explícitas de producto desktop offline-first y sincronización eventual con Google Sheets.
