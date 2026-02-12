CREATE UNIQUE INDEX IF NOT EXISTS ux_personas_uuid
ON personas(uuid);

CREATE UNIQUE INDEX IF NOT EXISTS ux_solicitudes_uuid
ON solicitudes(uuid);
