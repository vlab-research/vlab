CREATE TABLE users(
       id VARCHAR PRIMARY KEY
);

CREATE TABLE studies(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       slug VARCHAR NOT NULL,
       name string NOT NULL,
       created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       user_id VARCHAR NOT NULL REFERENCES users(id),
       credentials_key VARCHAR,
       credentials_entity VARCHAR DEFAULT 'facebook_ad_user',
       CONSTRAINT unique_name UNIQUE(user_id, name),
       CONSTRAINT unique_slug UNIQUE(user_id, slug)
);

CREATE TABLE study_confs(
       created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
       study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
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
       user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       entity VARCHAR NOT NULL,
       key VARCHAR NOT NULL,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       details JSONB NOT NULL
);

ALTER TABLE credentials ADD CONSTRAINT unique_entity_key_per_user UNIQUE(user_id, entity, key);


CREATE TABLE adopt_reports(
       study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       report_type VARCHAR NOT NULL,
       details JSONB NOT NULL
);

CREATE index ON studies (user_id, credentials_entity, credentials_key);
ALTER TABLE studies ADD CONSTRAINT credentials_key_exists FOREIGN KEY (user_id, credentials_entity, credentials_key) REFERENCES credentials (user_id, entity, key);

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
         (conf->>'start_date')::TIMESTAMP as start_date,
         (conf->>'end_date')::TIMESTAMP as end_date
  FROM t
  INNER JOIN studies ON t.study_id = studies.id
  WHERE conf_type = 'recruitment'
  AND n = 1
);
