CREATE TABLE chatroach.credentials(
       userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
       entity VARCHAR NOT NULL,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       details JSONB NOT NULL,
       INDEX (userid, entity, created desc) STORING (details)
);


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

GRANT INSERT,SELECT,UPDATE ON TABLE chatroach.credentials to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatroach;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatroach;


GRANT SELECT ON TABLE chatroach.credentials to chatreader;
GRANT INSERT,SELECT ON TABLE chatroach.campaigns to chatreader;
GRANT INSERT,SELECT ON TABLE chatroach.campaign_confs to chatreader;
