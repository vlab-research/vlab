/* USAGE AT SETUP:
*****************
cat chatroach.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach --restart=Never --command -- ./cockroach sql --insecure --host chatroach-cockroachdb-public.default
*****************
*/

CREATE DATABASE chatroach;

-- TODO: add userid that's not the end user, but the survey owner...
CREATE TABLE chatroach.messages(
       id BIGINT PRIMARY KEY,
       content VARCHAR NOT NULL,
       userid VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL
);


CREATE TABLE chatroach.users(
       id VARCHAR NOT NULL PRIMARY KEY,
       token VARCHAR NOT NULL,
       email VARCHAR NOT NULL UNIQUE
);

CREATE TABLE chatroach.surveys(
       id VARCHAR NOT NULL PRIMARY KEY,
       formid VARCHAR NOT NULL,
       form VARCHAR NOT NULL,
       messages VARCHAR,
       shortcode INT NOT NULL,
       title VARCHAR NOT NULL,
       userid VARCHAR NOT NULL REFERENCES chatroach.users(email) ON DELETE CASCADE
);

CREATE TABLE chatroach.responses(
       formid VARCHAR NOT NULL REFERENCES chatroach.surveys(id),
       flowid INT NOT NULL,
       userid VARCHAR NOT NULL,
       question_ref VARCHAR NOT NULL,
       question_idx INT NOT NULL,
       question_text VARCHAR NOT NULL,
       response VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL,
       PRIMARY KEY (userid, timestamp)
);

CREATE TABLE chatroach.timeouts(
       userid VARCHAR NOT NULL,
       timeout_date TIMESTAMPTZ,
       fulfilled BOOLEAN,
       PRIMARY KEY (userid, timeout_date)
);


CREATE USER chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.messages to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.responses to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.timeouts to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.users to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.surveys to chatroach;
