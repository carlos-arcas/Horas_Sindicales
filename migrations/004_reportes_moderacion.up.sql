CREATE TABLE IF NOT EXISTS reportes_contenido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporte_uuid TEXT NOT NULL UNIQUE,
    denunciante_id TEXT NOT NULL,
    recurso_tipo TEXT NOT NULL,
    recurso_id TEXT NOT NULL,
    motivo TEXT NOT NULL,
    detalle TEXT NULL,
    estado TEXT NOT NULL,
    accion_moderacion TEXT NULL,
    admin_resolutor_id TEXT NULL,
    comentario_admin TEXT NULL,
    fecha_creacion TEXT NOT NULL,
    fecha_resolucion TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_reportes_estado_fecha
ON reportes_contenido (estado, fecha_creacion DESC);

CREATE INDEX IF NOT EXISTS idx_reportes_recurso
ON reportes_contenido (recurso_tipo, recurso_id);

CREATE INDEX IF NOT EXISTS idx_reportes_denunciante_estado
ON reportes_contenido (denunciante_id, estado);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reporte_pendiente_denunciante_recurso
ON reportes_contenido (denunciante_id, recurso_tipo, recurso_id)
WHERE estado = 'pendiente';

CREATE TABLE IF NOT EXISTS auditoria_seguridad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_evento TEXT NOT NULL,
    resultado TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    recurso_tipo TEXT NOT NULL,
    recurso_id TEXT NOT NULL,
    fecha_evento TEXT NOT NULL
);
