ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

ALTER TABLE chatroach.surveys ADD COLUMN metadata JSONB SET DEFAULT '{}';
ALTER TABLE chatroach.surveys ADD COLUMN survey_name VARCHAR SET DEFAULT 'default';
ALTER TABLE chatroach.surveys ADD COLUMN translation_conf JSONB SET DEFAULT '{}';
