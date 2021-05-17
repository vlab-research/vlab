ALTER TABLE chatroach.states ADD COLUMN error_tag VARCHAR AS (state_json->'error'->>'tag') STORED;

CREATE INDEX ON chatroach.states (error_tag, current_state, current_form, updated);
