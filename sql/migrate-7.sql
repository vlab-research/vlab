-- More indices
CREATE INDEX ON chatroach.responses (surveyid, timestamp DESC);
CREATE INDEX ON chatroach.surveys (shortcode, created);
