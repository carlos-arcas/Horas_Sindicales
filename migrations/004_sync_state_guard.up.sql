CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    last_sync_at TEXT NULL
);

INSERT OR IGNORE INTO sync_state (id, last_sync_at)
VALUES (1, NULL);
