-- states

-- Add created columns
ALTER TABLE chatroach.states ADD COLUMN fb_error_code varchar AS (state_json->'error'->>'code') STORED;
ALTER TABLE chatroach.states ADD COLUMN timeout_date TIMESTAMPTZ AS (CASE
      WHEN state_json->'wait'->>'type' = 'timeout' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL)
      ELSE NULL
END) STORED;


-- Index those columns for queries!
-- TODO: Should include updated, for time window filtering in grafana!!
CREATE INDEX ON chatroach.states (current_state, fb_error_code) STORING (state_json);
CREATE INDEX ON chatroach.states (current_state, timeout_date) STORING (state_json);
