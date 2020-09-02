ALTER TABLE chatroach.states ADD CONSTRAINT "valid_state_json" CHECK (state_json ? 'state');
ALTER TABLE chatroach.responses ADD CONSTRAINT "valid_metadata" CHECK (json_typeof(metadata) = 'object');
