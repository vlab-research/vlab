-- NOTE: Every future schema change to ad_attributions touches both paths
-- (golang-migrate here AND devops/helm/migrations/init.sql).
--
-- vlab owns the ad -> stratum join. vlab creates exactly one ad per
-- (creative, stratum) pair, so the ad id already determines the shortcode,
-- the creative and the stratum metadata. This table is that mapping, written
-- once at ad-creation time and joined against later, replacing the dotted ref
-- string that used to ride to the survey platform inside every message.
--
-- Three invariants hold this table up. All three are load-bearing; see
-- planning/ad-id-attribution.md.
--
-- 1. `metadata` is the complete key/value set the ref would have carried --
--    `{"creative": <creative_name>, **md}` where md is what create_creative
--    builds and hands to make_ref. It is NOT stratum.metadata: that omits the
--    `creative` and `form` keys, and a downstream extraction conf asking for
--    either would silently match no stratum and the optimizer would reallocate
--    budget away from it.
--
-- 2. Append-only. Never delete a row, never rebuild the table from live
--    Facebook state. Reconciliation deletes ads that fall out of the desired
--    set, but respondents keep arriving from deleted ads -- CTWA referrals
--    carry ads_context_data.post_id and page posts persist and can be reshared
--    indefinitely. A row must outlive its ad. Hence: no TTL (unlike
--    study_run_events) and no FOREIGN KEY to studies, because a cascading
--    delete is a delete path and this table has none.
--
-- 3. `metadata` is frozen at creation, permanently. Study confs mutate, so a
--    stratum's metadata today is not what it was when the ad was created --
--    which is why even a live ad cannot be resolved by reading the current
--    conf. The row is a snapshot, not a pointer. Writes use ON CONFLICT DO
--    NOTHING so a re-run can never overwrite the original snapshot.
CREATE TABLE ad_attributions (
       network       STRING      NOT NULL DEFAULT 'facebook', -- ad network, NOT messaging channel: messenger and whatsapp ads are both 'facebook'
       ad_id         STRING      NOT NULL,                    -- the id Meta returned when we created the ad
       study_id      UUID        NOT NULL,                    -- no FK: see invariant 2
       stratum_id    STRING      NOT NULL,                    -- == the adset name
       creative_name STRING      NOT NULL,                    -- == the ad name
       shortcode     STRING,                                  -- routing token; NULL for web/app destinations
       metadata      JSONB       NOT NULL,                    -- frozen ref-equivalent blob: see invariant 1
       resolved_from STRING,                                  -- which id source produced ad_id: 'ad_id' | 'source_id'
       created       TIMESTAMPTZ NOT NULL DEFAULT now(),
       CONSTRAINT ad_attributions_pk PRIMARY KEY (network, ad_id)
);

-- The join the CSV export and swoosh both need: every ad for one study.
CREATE INDEX idx_ad_attributions_study ON ad_attributions (study_id);
