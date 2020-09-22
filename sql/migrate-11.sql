ALTER TABLE states ADD COLUMN error_tag VARCHAR AS (state_json->'error'->>'tag') STORED;
