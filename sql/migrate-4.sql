-- states

-- Add created columns
ALTER TABLE chatroach.states ADD COLUMN fb_error_code varchar AS (state_json->'error'->>'code') STORED;
ALTER TABLE chatroach.states ADD COLUMN timeout_date TIMESTAMPTZ AS (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL) STORED;

-- Index those columns for queries!
CREATE INDEX ON chatroach.states (current_state, fb_error_code) STORING (state_json);
CREATE INDEX ON chatroach.states (current_state, timeout_date) STORING (state_json);



