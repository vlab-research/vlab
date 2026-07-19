-- NOTE: Every future schema change to study_run_events touches both paths
-- (golang-migrate here AND devops/helm/migrations/init.sql).
CREATE TABLE study_run_events (
    study_id    UUID   NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    source      STRING NOT NULL,            -- 'inference' | 'connector:fly' | 'optimizer' | 'config' (future)
    run_id      STRING NOT NULL DEFAULT '', -- groups facts of one run / one validation pass
    event_type  STRING NOT NULL,            -- 'run_started'|'run_ok'|'run_error'|'extraction_error'|'extraction_warning'|'heartbeat'|'heartbeat_missing'
    fingerprint STRING NOT NULL DEFAULT '', -- stable grouping key; ok/error share a fingerprint to close
    severity    STRING NOT NULL DEFAULT '', -- 'error'|'warning'|'' for non-problem facts
    message     STRING NOT NULL DEFAULT '', -- human-readable, shown in the banner
    details     JSON,                       -- structured context (offending value, count, sources-in-mapping, etc.)
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_id    UUID   NOT NULL DEFAULT gen_random_uuid(),
    CONSTRAINT study_run_events_pk PRIMARY KEY (study_id, occurred_at, event_id)
) WITH (ttl_expire_after = '90 days', ttl_job_cron = '@daily');

-- Covering index for the "latest event per group, for one study" derivation query:
CREATE INDEX idx_study_run_events_group
  ON study_run_events (study_id, source, fingerprint, occurred_at DESC)
  STORING (event_type, severity, message, details);
