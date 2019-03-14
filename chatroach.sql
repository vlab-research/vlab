/* USAGE AT SETUP:
*****************
cat chatroach.sql | kubectl run -i --rm cockroach-client devops master --image=cockroachdb/cockroach --restart=Never --command ./cockroach sql --insecure --host chatroach-cockroachdb-public.default
*****************
*/

CREATE DATABASE chatroach;

CREATE TABLE chatroach.messages(
       id BIGINT PRIMARY KEY,
       content VARCHAR NOT NULL,
       userid VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE chatroach.responses(
       formid VARCHAR NOT NULL,
       flowid INT NOT NULL,
       userid VARCHAR NOT NULL,
       question_ref VARCHAR NOT NULL,
       question_idx INT NOT NULL,
       question_text VARCHAR NOT NULL,
       response VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL,
       PRIMARY KEY (userid, timestamp)
);

CREATE USER chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.messages to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.responses to chatroach;
