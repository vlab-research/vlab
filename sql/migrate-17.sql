-- DROP OLD INDEX/COLUMN FOR TIMEOUTS

DROP index IF EXISTS states_current_state_timeout_date_idx;

SET sql_safe_updates=FALSE;
ALTER TABLE chatroach.states DROP COLUMN timeout_date;
SET sql_safe_updates=TRUE;

-- CREATE NEW INDEX/COLUMN FOR TIMEOUTS
ALTER TABLE chatroach.states ADD COLUMN timeout_date TIMESTAMPTZ AS (CASE
      WHEN state_json->'wait'->>'type' = 'timeout' AND state_json->'wait'->'value'->>'type' = 'absolute' THEN (state_json->'wait'->'value'->>'timeout')::TIMESTAMPTZ
      WHEN state_json->'wait'->>'type' = 'timeout' AND state_json->'wait'->'value'->>'type' = 'relative' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->'value'->>'timeout')::INTERVAL)
      WHEN state_json->'wait'->>'type' = 'timeout' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL)
      ELSE NULL
END) STORED;

CREATE INDEX ON chatroach.states (current_state, timeout_date) STORING (state_json);
