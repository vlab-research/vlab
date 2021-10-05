CREATE TABLE studies(
       user_id UUID,
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       name string NOT NULL,
       active bool NOT NULL,
       CONSTRAINT unique_name UNIQUE(user_id, name)
);

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
       timestamp TIMESTAMPTZ NOT NULL,
       updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
