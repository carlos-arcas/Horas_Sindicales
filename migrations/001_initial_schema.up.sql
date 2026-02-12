CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    genero TEXT NOT NULL CHECK(genero IN ('M','F')),
    horas_mes_min INTEGER,
    horas_ano_min INTEGER,
    horas_jornada_defecto_min INTEGER,
    is_active INTEGER DEFAULT 1,
    cuad_lun_man_min INTEGER,
    cuad_lun_tar_min INTEGER,
    cuad_mar_man_min INTEGER,
    cuad_mar_tar_min INTEGER,
    cuad_mie_man_min INTEGER,
    cuad_mie_tar_min INTEGER,
    cuad_jue_man_min INTEGER,
    cuad_jue_tar_min INTEGER,
    cuad_vie_man_min INTEGER,
    cuad_vie_tar_min INTEGER,
    cuad_sab_man_min INTEGER,
    cuad_sab_tar_min INTEGER,
    cuad_dom_man_min INTEGER,
    cuad_dom_tar_min INTEGER,
    cuadrante_uniforme INTEGER DEFAULT 0,
    trabaja_finde INTEGER DEFAULT 0,
    uuid TEXT,
    updated_at TEXT,
    source_device TEXT,
    deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS solicitudes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id INTEGER NOT NULL,
    fecha_solicitud TEXT NOT NULL,
    fecha_pedida TEXT NOT NULL,
    desde_min INTEGER NULL,
    hasta_min INTEGER NULL,
    completo INTEGER NOT NULL,
    horas_solicitadas_min INTEGER,
    observaciones TEXT NULL,
    notas TEXT NULL,
    pdf_path TEXT NULL,
    pdf_hash TEXT NULL,
    generated INTEGER NOT NULL DEFAULT 1,
    uuid TEXT,
    updated_at TEXT,
    source_device TEXT,
    deleted INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(persona_id) REFERENCES personas(id)
);

CREATE INDEX IF NOT EXISTS idx_sol_persona_fecha_pedida
ON solicitudes (persona_id, fecha_pedida);

CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    last_sync_at TEXT NULL
);

INSERT OR IGNORE INTO sync_state (id, last_sync_at)
VALUES (1, NULL);

CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    local_snapshot_json TEXT NOT NULL,
    remote_snapshot_json TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cuadrantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    delegada_uuid TEXT NOT NULL,
    dia_semana TEXT NOT NULL,
    man_min INTEGER,
    tar_min INTEGER,
    updated_at TEXT,
    source_device TEXT,
    deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pdf_log (
    pdf_id TEXT PRIMARY KEY,
    delegada_uuid TEXT,
    rango_fechas TEXT,
    fecha_generacion TEXT,
    hash TEXT,
    updated_at TEXT,
    source_device TEXT
);

CREATE TABLE IF NOT EXISTS sync_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT,
    source_device TEXT
);

CREATE TABLE IF NOT EXISTS grupo_config (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    nombre_grupo TEXT NULL,
    bolsa_anual_grupo_min INTEGER DEFAULT 0,
    pdf_logo_path TEXT DEFAULT 'logo.png',
    pdf_intro_text TEXT DEFAULT 'Conforme a lo dispuesto en el art.68 e) del Estatuto de los Trabajadores, aprobado por el Real Decreto Legislativo 1/1995 de 24 de marzo, dispense la ausencia al trabajo de los/as trabajadores/as que a continuación se relacionan, los cuales han de resolver asuntos relativos al ejercicio de sus funciones, representando al personal de su empresa.',
    pdf_include_hours_in_horario INTEGER NULL
);

INSERT OR IGNORE INTO grupo_config (
    id, nombre_grupo, bolsa_anual_grupo_min, pdf_logo_path, pdf_intro_text, pdf_include_hours_in_horario
) VALUES (
    1, NULL, 0, 'logo.png',
    'Conforme a lo dispuesto en el art.68 e) del Estatuto de los Trabajadores, aprobado por el Real Decreto Legislativo 1/1995 de 24 de marzo, dispense la ausencia al trabajo de los/as trabajadores/as que a continuación se relacionan, los cuales han de resolver asuntos relativos al ejercicio de sus funciones, representando al personal de su empresa.',
    NULL
);
