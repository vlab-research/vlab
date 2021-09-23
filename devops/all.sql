/* USAGE AT SETUP:
*****************
export VLAB_NAME=foo
cat chatroach.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v19.2.3 --restart=Never --command -- ./cockroach sql --insecure --host ${VLAB_NAME}-cockroachdb-public.default
*****************
*/

CREATE DATABASE chatroach;

-- TODO: add userid that's not the end user, but the survey owner...
-- OR JUST THE PAGEID, FOR EXAMPLE!
-- TODO: Make primary key id + userid!
-- PRIMARY KEY (userid, timestamp, question_ref), -- bit hacky, remove timestamp?
CREATE TABLE chatroach.messages(
       id BIGINT PRIMARY KEY,
       content VARCHAR NOT NULL,
       userid VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL,
       INDEX (userid) STORING (content, timestamp)
);

CREATE TABLE chatroach.users(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       token VARCHAR NOT NULL,
       email VARCHAR NOT NULL UNIQUE
);

CREATE TABLE chatroach.facebook_pages(
       pageid VARCHAR PRIMARY KEY,
       userid UUID REFERENCES chatroach.users(id) ON DELETE CASCADE
);

CREATE TABLE chatroach.surveys(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       created TIMESTAMPTZ NOT NULL,
       formid VARCHAR NOT NULL,
       form VARCHAR NOT NULL,
       messages VARCHAR,
       shortcode VARCHAR NOT NULL,
       title VARCHAR NOT NULL,
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE
);

CREATE TABLE chatroach.responses(
       parent_surveyid UUID NOT NULL REFERENCES chatroach.surveys(id),
       parent_shortcode VARCHAR NOT NULL, -- implicit reference to surveys.shortcode
       surveyid UUID NOT NULL REFERENCES chatroach.surveys(id),
       shortcode VARCHAR NOT NULL, -- implicit reference to surveys.shortcode
       flowid INT NOT NULL,
       userid VARCHAR NOT NULL,
       question_ref VARCHAR NOT NULL,
       question_idx INT NOT NULL,
       question_text VARCHAR NOT NULL,
       response VARCHAR NOT NULL,
       seed INT NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL,
       PRIMARY KEY (userid, timestamp, question_ref) -- bit hacky, remove timestamp?
);

CREATE TABLE chatroach.timeouts(
       userid VARCHAR NOT NULL,
       pageid VARCHAR NOT NULL REFERENCES chatroach.facebook_pages(pageid),
       timeout_date TIMESTAMPTZ,
       fulfilled BOOLEAN,
       PRIMARY KEY (userid, timeout_date),
       INDEX (fulfilled, timeout_date) STORING (pageid)
);


CREATE USER chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.messages to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.responses to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.timeouts to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.users to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.surveys to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.facebook_pages to chatroach;

CREATE USER chatreader;
GRANT SELECT ON TABLE chatroach.messages to chatreader;
GRANT SELECT ON TABLE chatroach.responses to chatreader;
GRANT SELECT ON TABLE chatroach.timeouts to chatreader;
GRANT SELECT ON TABLE chatroach.users to chatreader;
GRANT SELECT ON TABLE chatroach.surveys to chatreader;
GRANT SELECT ON TABLE chatroach.facebook_pages to chatreader;
-- CREATE TABLE chatroach.projects(
--        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--        name VARCHAR NOT NULL
-- );

-- CREATE TABLE chatroach.users_projects(
--        userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
--        projectid UUID NOT NULL REFERENCES chatroach.projects(id) ON DELETE CASCADE
-- );

ALTER TABLE chatroach.facebook_pages ADD COLUMN token VARCHAR;
-- ALTER TABLE chatroach.facebook_pages ADD COLUMN projectid UUID REFERENCES chatroach.projects(id) ON DELETE CASCADE;


-- ALTER TABLE chatroach.surveys ADD COLUMN projectid UUID REFERENCES chatroach.projects(id) ON DELETE CASCADE;
ALTER TABLE chatroach.responses ADD COLUMN metadata JSONB;
CREATE TABLE chatroach.states(
       userid VARCHAR NOT NULL,
       pageid VARCHAR NOT NULL NOT NULL REFERENCES chatroach.facebook_pages(pageid),
       updated TIMESTAMPTZ NOT NULL,
       current_state VARCHAR NOT NULL,
       state_json JSON NOT NULL,
       PRIMARY KEY (userid, pageid),
       INDEX (current_state, updated)
);

GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.states to chatroach;
-- states

-- Add created columns
ALTER TABLE chatroach.states ADD COLUMN fb_error_code varchar AS (state_json->'error'->>'code') STORED;
ALTER TABLE chatroach.states ADD COLUMN timeout_date TIMESTAMPTZ AS (CASE
      WHEN state_json->'wait'->>'type' = 'timeout' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL)
      ELSE NULL
END) STORED;


-- Index those columns for queries!
-- TODO: Should include updated, for time window filtering in grafana!!
CREATE INDEX ON chatroach.states (current_state, fb_error_code) STORING (state_json);
-- CREATE INDEX ON chatroach.states (current_state, timeout_date) STORING (state_json);
-- messages updates!

-- fix weird farmhash int and make reasonable primary key!
ALTER TABLE chatroach.messages ADD COLUMN hsh INT AS (fnv64a(content)) STORED NOT NULL;
BEGIN;
ALTER TABLE chatroach.messages DROP CONSTRAINT "primary";
ALTER TABLE chatroach.messages ADD CONSTRAINT "primary" PRIMARY KEY (hsh, userid);
COMMIT;

ALTER TABLE chatroach.messages ALTER COLUMN id DROP NOT NULL;

-- indices
CREATE INDEX ON chatroach.messages (userid, timestamp ASC) STORING (content);
ALTER TABLE chatroach.responses ADD COLUMN pageid VARCHAR;
ALTER TABLE chatroach.responses ALTER COLUMN parent_surveyid DROP NOT NULL;

ALTER TABLE chatroach.states DROP CONSTRAINT fk_pageid_ref_facebook_pages;
CREATE INVERTED INDEX ON chatroach.states(state_json);

CREATE INVERTED INDEX ON chatroach.responses(metadata);

ALTER TABLE chatroach.states ADD COLUMN current_form varchar AS (state_json->'forms'->>-1) STORED;
CREATE INDEX ON chatroach.states (current_state, current_form, updated);

ALTER TABLE chatroach.surveys ADD COLUMN form_json JSON AS (form::JSON) STORED;
CREATE INDEX ON chatroach.surveys (shortcode, userid, created DESC) STORING (formid, form, messages, title, form_json);

ALTER TABLE chatroach.surveys ADD COLUMN messages_json JSON AS (messages::JSON) STORED;
ALTER TABLE chatroach.surveys ADD COLUMN has_followup BOOL AS (messages::JSON->>'label.buttonHint.default' IS NOT NULL) STORED;

-- this index doesn't seem to help the followups query
CREATE INDEX ON chatroach.surveys (has_followup, shortcode, userid, created desc);
ALTER TABLE chatroach.states ADD COLUMN previous_is_followup BOOL AS (state_json->'previousOutput'->>'followUp' IS NOT NULL) STORED;
ALTER TABLE chatroach.states ADD COLUMN previous_with_token BOOL AS (state_json->'previousOutput'->>'token' IS NOT NULL) STORED;
ALTER TABLE chatroach.states ADD COLUMN form_start_time TIMESTAMPTZ AS (CEILING((state_json->'md'->>'startTime')::INT/1000)::INT::TIMESTAMPTZ) STORED;

CREATE INDEX ON chatroach.states (previous_with_token, previous_is_followup, form_start_time, current_state, updated) STORING (state_json);
ALTER TABLE chatroach.states ADD COLUMN error_tag VARCHAR AS (state_json->'error'->>'tag') STORED;

CREATE INDEX ON chatroach.states (error_tag, current_state, current_form, updated);
ALTER TABLE chatroach.states ADD COLUMN stuck_on_question VARCHAR AS (CASE WHEN (state_json->'qa'->-1->>0) = (state_json->'qa'->-2->>0) AND (state_json->'qa'->-2->>0) = (state_json->'qa'->-3->>0) THEN state_json->'qa'->-1->>0 ELSE NULL END) STORED;

CREATE INDEX ON chatroach.states (stuck_on_question, current_state, current_form, updated);
ALTER TABLE chatroach.responses ADD COLUMN clusterid VARCHAR AS (metadata->>'clusterid') STORED;

CREATE INDEX ON chatroach.responses (shortcode, question_ref, response, clusterid, timestamp);
ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

ALTER TABLE chatroach.surveys ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE chatroach.surveys ADD COLUMN survey_name VARCHAR NOT NULL DEFAULT 'default';
ALTER TABLE chatroach.surveys ADD COLUMN translation_conf JSONB NOT NULL DEFAULT '{}';
CREATE TABLE chatroach.credentials(
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
       entity VARCHAR NOT NULL,
       key VARCHAR NOT NULL,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       details JSONB NOT NULL,
       UNIQUE(entity, key),
       INDEX (userid, entity, key, created desc) STORING (details)
);

-- add unique constraint to facebook_page_id, then force updating rather than just posting
-- on conflict insert for post...
ALTER TABLE chatroach.credentials ADD COLUMN facebook_page_id VARCHAR AS (CASE WHEN entity = 'facebook_page' THEN details->>'id' ELSE NULL END) STORED;
ALTER TABLE chatroach.credentials ADD CONSTRAINT unique_facebook_page UNIQUE(facebook_page_id);
CREATE INDEX ON chatroach.credentials(facebook_page_id) STORING (details, key, userid);

GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.credentials to chatroach;
GRANT SELECT ON TABLE chatroach.credentials to chatreader;


ALTER TABLE chatroach.facebook_pages ADD COLUMN instagramid VARCHAR;


CREATE TABLE chatroach.campaigns(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       name VARCHAR NOT NULL,
       UNIQUE (userid, name)
);

CREATE TABLE chatroach.campaign_confs(
       campaignid UUID NOT NULL REFERENCES chatroach.campaigns(id) ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       conf_type VARCHAR NOT NULL,
       entity_name VARCHAR,
       conf JSONB NOT NULL,
       INDEX (campaignid, conf_type, created desc) STORING (entity_name, conf)
);

GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatreader;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatreader;
CREATE INDEX ON chatroach.messages (timestamp DESC) STORING (content);

-- REMOVE TOKEN FROM USERS AND ADD TO CREDENTIALS
SET sql_safe_updates=false;
ALTER TABLE chatroach.users DROP COLUMN token;
SET sql_safe_updates=true;

DROP TABLE chatroach.timeouts;
DROP TABLE chatroach.facebook_pages;
-- DROP OLD INDEX/COLUMN FOR TIMEOUTS

DROP INDEX IF EXISTS states_current_state_timeout_date_idx;

SET sql_safe_updates=FALSE;
ALTER TABLE chatroach.states DROP COLUMN timeout_date;
SET sql_safe_updates=TRUE;

-- CREATE NEW INDEX/COLUMN FOR TIMEOUTS
ALTER TABLE chatroach.states ADD COLUMN timeout_date TIMESTAMPTZ AS (CASE
      WHEN state_json->'wait'->>'type' = 'timeout' AND state_json->'wait'->'value'->>'type' = 'absolute' THEN (state_json->'wait'->'value'->>'timeout')::TIMESTAMPTZ
      WHEN state_json->'wait'->>'type' = 'timeout' AND state_json->'wait'->'value'->>'type' = 'relative' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->'value'->>'timeout')::INTERVAL)
      WHEN state_json->'wait'->>'type' = 'timeout' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL)
      ELSE NULL
END) STORED;

CREATE INDEX ON chatroach.states (current_state, timeout_date) STORING (state_json);
ALTER TABLE chatroach.campaigns ADD COLUMN active BOOL NOT NULL DEFAULT TRUE;

CREATE TABLE chatroach.adopt_reports(
       campaignid UUID NOT NULL REFERENCES chatroach.campaigns ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       report_type VARCHAR NOT NULL,
       details JSONB NOT NULL
);

GRANT INSERT,SELECT ON TABLE chatroach.adopt_reports to chatroach;
GRANT SELECT ON TABLE chatroach.adopt_reports to chatreader;

CREATE USER adopt;
GRANT SELECT ON TABLE chatroach.responses to adopt;
GRANT SELECT ON TABLE chatroach.credentials to adopt;
GRANT SELECT ON TABLE chatroach.surveys to adopt;
GRANT SELECT ON TABLE chatroach.campaigns to adopt;
GRANT SELECT ON TABLE chatroach.campaign_confs to adopt;
GRANT INSERT,SELECT ON TABLE chatroach.adopt_reports to adopt;


-- TODO: remove index and remove foreign key constraint
-- campaign_confs_campaignid_conf_type_created_idx
-- SET sql_safe_updates=FALSE;
-- ALTER TABLE chatroach.campaign_confs DROP COLUMN entity_name;
-- SET sql_safe_updates=TRUE;
CREATE INDEX ON chatroach.responses (surveyid, userid, timestamp asc, question_ref) storing (parent_surveyid, parent_shortcode, shortcode, flowid, question_idx, question_text, response, seed, metadata, pageid, clusterid, translated_response);
ALTER TABLE chatroach.states ADD COLUMN next_retry TIMESTAMP AS ((FLOOR((POWER(2, (CASE WHEN JSON_ARRAY_LENGTH(state_json->'retries') <= 16 THEN JSON_ARRAY_LENGTH(state_json->'retries') ELSE 16 END))*60000 + (state_json->'retries'->>-1)::INT)::INT)/1000)::INT::TIMESTAMP) STORED;

CREATE INDEX ON chatroach.states (current_state, error_tag, updated, next_retry);
CREATE INDEX ON chatroach.states (current_state, fb_error_code, updated, next_retry);
