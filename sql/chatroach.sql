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
