CREATE TABLE IF NOT EXISTS comunidad_perfiles (
    perfil_id TEXT PRIMARY KEY,
    alias TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    disciplina_principal TEXT NOT NULL,
    seguidores INTEGER NOT NULL DEFAULT 0,
    activo INTEGER NOT NULL DEFAULT 1,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comunidad_publicaciones (
    publicacion_id TEXT PRIMARY KEY,
    perfil_id TEXT NOT NULL,
    disciplina TEXT NOT NULL,
    titulo TEXT NOT NULL,
    resumen TEXT NOT NULL DEFAULT '',
    likes INTEGER NOT NULL DEFAULT 0,
    comentarios INTEGER NOT NULL DEFAULT 0,
    publicado_en TEXT NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(perfil_id) REFERENCES comunidad_perfiles(perfil_id)
);

CREATE INDEX IF NOT EXISTS idx_comunidad_publicaciones_disciplina
    ON comunidad_publicaciones(disciplina, publicado_en DESC);

CREATE INDEX IF NOT EXISTS idx_comunidad_publicaciones_populares
    ON comunidad_publicaciones(likes DESC, comentarios DESC);
