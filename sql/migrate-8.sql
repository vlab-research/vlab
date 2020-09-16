CREATE INVERTED INDEX ON chatroach.states(state_json);

CREATE INVERTED INDEX ON chatroach.responses(metadata);

ALTER TABLE chatroach.states ADD COLUMN current_form varchar AS (state_json->'forms'->>-1) STORED;
CREATE INDEX ON chatroach.states (current_state, current_form, updated);

ALTER TABLE chatroach.surveys ADD COLUMN form_json JSON AS (form::JSON) STORED;
CREATE INDEX ON chatroach.surveys (shortcode, userid, pageid, created DESC) STORING (formid, form, messages, title, form_json);

ALTER TABLE chatroach.surveys ADD COLUMN messages_json JSON AS (messages::JSON) STORED;
ALTER TABLE chatroach.surveys ADD COLUMN has_followup BOOL AS (messages::JSON->>'label.buttonHint.default' IS NOT NULL) STORED;

-- this index doesn't seem to help the followups query
CREATE INDEX ON chatroach.surveys (has_followup, shortcode, userid, created desc);
