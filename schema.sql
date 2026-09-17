PRAGMA foreign_keys = ON;
PRAGMA recursive_triggers = ON;
-- Bronze stores exact delivered bytes, keyed by their SHA-256; payloads never change.
CREATE TABLE IF NOT EXISTS bronze (
    sha256 TEXT PRIMARY KEY,
    payload BLOB NOT NULL,
    source_kind TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS bronze_no_update BEFORE UPDATE ON bronze
BEGIN SELECT RAISE(ABORT, 'bronze is immutable'); END;
CREATE TRIGGER IF NOT EXISTS bronze_no_delete BEFORE DELETE ON bronze
BEGIN SELECT RAISE(ABORT, 'bronze is immutable'); END;
-- Work identity, never DOI alone, is the materialization key.
CREATE TABLE IF NOT EXISTS silver (
    work_id TEXT PRIMARY KEY,
    content_sha256 TEXT NOT NULL,
    normalized_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    bronze_sha256 TEXT NOT NULL REFERENCES bronze(sha256)
);
CREATE TABLE IF NOT EXISTS replay_runs (
    run_id INTEGER PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
    finding_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES replay_runs(run_id),
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);
