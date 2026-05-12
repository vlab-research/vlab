CREATE TABLE connector_runs (
  study_id    UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  run_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  events_written INTEGER NOT NULL
);

CREATE INDEX idx_connector_runs_lookup
  ON connector_runs (study_id, source_name, run_at DESC);
