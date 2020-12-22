CREATE INDEX ON chatroach.messages (timestamp) STORING (userid);
CREATE INDEX ON chatroach.messages (timestamp) STORING (userid, content);
