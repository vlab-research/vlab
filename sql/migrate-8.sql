CREATE INVERTED INDEX ON chatroach.states(state_json);

ALTER TABLE chatroach.states ADD COLUMN current_form varchar AS (state_json->'forms'->>-1) STORED;
CREATE INDEX ON chatroach.states (current_state, current_form, updated);

ALTER TABLE chatroach.surveys ADD COLUMN form_json JSON AS (form::JSON) STORED;
CREATE INDEX ON chatroach.surveys (shortcode, userid, pageid, created DESC) STORING (formid, form, messages, title, form_json);
