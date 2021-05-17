ALTER TABLE chatroach.campaigns ADD COLUMN active BOOL NOT NULL DEFAULT TRUE;

CREATE TABLE chatroach.adopt_reports(
       campaignid UUID NOT NULL REFERENCES chatroach.campaigns ON DELETE CASCADE,
       created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
       report_type VARCHAR NOT NULL,
       details JSONB NOT NULL
);

GRANT INSERT,SELECT ON TABLE chatroach.adopt_reports to chatroach;
GRANT SELECT ON TABLE chatroach.adopt_reports to chatreader;

CREATE USER adopt;
GRANT SELECT ON TABLE chatroach.responses to adopt;
GRANT SELECT ON TABLE chatroach.credentials to adopt;
GRANT SELECT ON TABLE chatroach.surveys to adopt;
GRANT SELECT ON TABLE chatroach.campaigns to adopt;
GRANT SELECT ON TABLE chatroach.campaign_confs to adopt;
GRANT INSERT,SELECT ON TABLE chatroach.adopt_reports to adopt;


-- TODO: remove index and remove foreign key constraint
-- campaign_confs_campaignid_conf_type_created_idx
-- SET sql_safe_updates=FALSE;
-- ALTER TABLE chatroach.campaign_confs DROP COLUMN entity_name;
-- SET sql_safe_updates=TRUE;
