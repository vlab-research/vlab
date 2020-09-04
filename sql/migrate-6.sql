ALTER TABLE chatroach.responses ADD COLUMN pageid VARCHAR;
ALTER TABLE chatroach.responses ALTER COLUMN parent_surveyid DROP NOT NULL;

