/* USAGE AT SETUP:
*****************
cat chatroach.sql | kubectl run -i --rm cockroach-client \                                                 ~/D/t/devops master
        --image=cockroachdb/cockroach \
        --restart=Never \
        --command -- ./cockroach sql --insecure --host chatroach-cockroachdb-public.default
*****************
*/

CREATE DATABASE chatroach;

CREATE TABLE chatroach.messages(
       id BIGINT PRIMARY KEY,
       content VARCHAR NOT NULL,
       userid VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL
);

CREATE USER chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.messages to chatroach;
