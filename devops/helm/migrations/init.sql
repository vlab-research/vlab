CREATE TABLE users(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       email VARCHAR NOT NULL UNIQUE
);

CREATE TABLE studies(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       user_id UUID NOT NULL REFERENCES users(id),
       name string NOT NULL,
       credentials_key VARCHAR,
       credentials_entity VARCHAR DEFAULT 'facebook_ad_user',
       CONSTRAINT unique_name UNIQUE(user_id, name)
);

-- view studies add active based on start/end date.



CREATE TABLE study_confs(
       created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
       study_id UUID NOT NULL REFERENCES studies(id),
       conf_type string NOT NULL,
       conf JSON NOT NULL
);



CREATE TABLE inference_data(
       study_id UUID NOT NULL REFERENCES studies(id),
       user_id VARCHAR NOT NULL,
       variable VARCHAR NOT NULL,
       value_type VARCHAR NOT NULL,
       value JSON NOT NULL,
       timestamp TIMESTAMP NOT NULL,
       updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       CONSTRAINT study_user UNIQUE(study_id, user_id, variable)
);

-- hash sharded index
CREATE TABLE inference_data_events(
       study_id UUID NOT NULL REFERENCES studies(id),
       source_name VARCHAR NOT NULL,
       timestamp TIMESTAMP NOT NULL,
       idx INT NOT NULL,
       pagination VARCHAR,
       data JSON NOT NULL
);

CREATE TABLE recruitment_data_events(
       study_id UUID NOT NULL REFERENCES studies(id),
       source_name VARCHAR NOT NULL,
       temp BOOLEAN NOT NULL,
       period_start TIMESTAMP NOT NULL,
       period_end TIMESTAMP NOT NULL,
       data JSON NOT NULL
);

ALTER TABLE recruitment_data_events ADD CONSTRAINT unique_per_period UNIQUE(study_id, source_name, temp, period_start, period_end);


CREATE TABLE credentials(
       user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       entity VARCHAR NOT NULL,
       key VARCHAR NOT NULL,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       details JSONB NOT NULL
);

ALTER TABLE credentials ADD CONSTRAINT unique_entity_key_per_user UNIQUE(user_id, entity, key);

-- CREATE index ON studies (userid, credentials_entity, credentials_key);
-- ALTER TABLE studies ADD CONSTRAINT credentials_key_exists FOREIGN KEY (userid, credentials_entity, credentials_key) REFERENCES credentials (userid, entity, key);

CREATE VIEW study_state AS (
  WITH t AS (
    SELECT created, study_id, conf_type, conf,
    ROW_NUMBER() OVER (PARTITION BY study_id, conf_type ORDER BY study_confs.created DESC) AS n
    FROM study_confs
  )
  SELECT id,
         studies.created,
         user_id,
         NAME,
         credentials_key,
         credentials_entity,
         ((conf->0->>'start_date')::TIMESTAMP < now() AND (conf->0->>'end_date')::TIMESTAMP > now()) AS active
  FROM t
  INNER JOIN studies ON t.study_id = studies.id
  WHERE conf_type = 'opt'
  AND n = 1
);

-- NOTE: Every future schema change to study_run_events touches both paths
-- (golang-migrate under devops/migrations/ AND this init.sql).
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
