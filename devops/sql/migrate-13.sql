ALTER TABLE chatroach.responses ADD COLUMN clusterid VARCHAR AS (metadata->>'clusterid') STORED;

CREATE INDEX ON chatroach.responses (shortcode, question_ref, response, clusterid, timestamp);
