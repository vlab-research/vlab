ALTER TABLE chatroach.states ADD COLUMN previous_is_followup BOOL AS (state_json->'previousOutput'->>'followUp' IS NOT NULL) STORED;
ALTER TABLE chatroach.states ADD COLUMN previous_with_token BOOL AS (state_json->'previousOutput'->>'token' IS NOT NULL) STORED;
ALTER TABLE chatroach.states ADD COLUMN form_start_time TIMESTAMPTZ AS (CEILING((state_json->'md'->>'startTime')::INT/1000)::INT::TIMESTAMPTZ) STORED;

CREATE INDEX ON chatroach.states (previous_with_token, previous_is_followup, form_start_time, current_state, updated) STORING (state_json);
