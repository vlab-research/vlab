ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

ALTER TABLE chatroach.surveys ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE chatroach.surveys ADD COLUMN survey_name VARCHAR NOT NULL DEFAULT 'default';
ALTER TABLE chatroach.surveys ADD COLUMN translation_conf JSONB NOT NULL DEFAULT '{}';
