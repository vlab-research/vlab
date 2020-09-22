CREATE TABLE chatroach.payments(
       userid VARCHAR NOT NULL,
       pageid VARCHAR NOT NULL REFERENCES chatroach.facebook_pages(pageid),
       timestamp TIMESTAMPTZ NOT NULL,
       provider VARCHAR NOT NULL,
       details JSON NOT NULL,
       results JSON,
       id INT AS (fnv64a(userid || pageid || timestamp::string)) STORED PRIMARY KEY,
       has_results BOOLEAN AS (CASE WHEN results IS NULL THEN FALSE ELSE TRUE END) STORED,
       INDEX (has_results, provider) STORING (userid, pageid, timestamp, details, results),
       INVERTED INDEX (results)
);

CREATE TABLE chatroach.credentials(
       userid UUID NOT NULL REFERENCES chatroach.users(id),
       entity VARCHAR NOT NULL,
       details JSON NOT NULL,
       PRIMARY KEY (userid, entity),
       INDEX (userid, entity) STORING (details)
);


GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.payments to chatroach;
GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.credentials to chatroach;
