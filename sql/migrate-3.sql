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
