CREATE TABLE chatroach.credentials(
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
       entity VARCHAR NOT NULL,
       key VARCHAR NOT NULL,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       details JSONB NOT NULL,
       UNIQUE(entity, key),
       INDEX (userid, entity, key, created desc) STORING (details)
);

-- add unique constraint to facebook_page_id, then force updating rather than just posting
-- on conflict insert for post...
ALTER TABLE chatroach.credentials ADD COLUMN facebook_page_id VARCHAR AS (CASE WHEN entity = 'facebook_page' THEN details->>'id' ELSE NULL END) STORED;
ALTER TABLE chatroach.credentials ADD CONSTRAINT unique_facebook_page UNIQUE(facebook_page_id);
CREATE INDEX ON chatroach.credentials(facebook_page_id) STORING (details, key, userid);

GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.credentials to chatroach;
GRANT SELECT ON TABLE chatroach.credentials to chatreader;


ALTER TABLE chatroach.facebook_pages ADD COLUMN instagramid VARCHAR;


CREATE TABLE chatroach.campaigns(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       name VARCHAR NOT NULL,
       UNIQUE (userid, name)
);

CREATE TABLE chatroach.campaign_confs(
       campaignid UUID NOT NULL REFERENCES chatroach.campaigns(id) ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       conf_type VARCHAR NOT NULL,
       entity_name VARCHAR,
       conf JSONB NOT NULL,
       INDEX (campaignid, conf_type, created desc) STORING (entity_name, conf)
);

GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatreader;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatreader;
