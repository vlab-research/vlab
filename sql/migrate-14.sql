ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

ALTER TABLE chatroach.surveys ADD COLUMN metadata JSONB DEFAULT '{}';
ALTER TABLE chatroach.surveys ADD COLUMN survey_name VARCHAR DEFAULT 'default';
ALTER TABLE chatroach.surveys ADD COLUMN translation_conf JSONB DEFAULT '{}';
