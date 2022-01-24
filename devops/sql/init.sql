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



-- ALTER TABLE credentials ADD CONSTRAINT unique_entity_key_per_user UNIQUE(userid, entity, key);

-- CREATE index ON studies (userid, credentials_entity, credentials_key);
-- ALTER TABLE studies ADD CONSTRAINT credentials_key_exists FOREIGN KEY (userid, credentials_entity, credentials_key) REFERENCES credentials (userid, entity, key);
