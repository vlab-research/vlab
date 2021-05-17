ALTER TABLE chatroach.states ADD COLUMN stuck_on_question VARCHAR AS (CASE WHEN (state_json->'qa'->-1->>0) = (state_json->'qa'->-2->>0) AND (state_json->'qa'->-2->>0) = (state_json->'qa'->-3->>0) THEN state_json->'qa'->-1->>0 ELSE NULL END) STORED;

CREATE INDEX ON chatroach.states (stuck_on_question, current_state, current_form, updated);
