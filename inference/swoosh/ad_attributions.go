package main

// The read side of the ad -> stratum mapping vlab freezes at ad-creation time
// (adopt/adopt/campaign_queries.py:create_ad_attribution). See
// documentation/ad-attributions.md and planning/ad-id-attribution.md.

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v4/pgxpool"
)

// AdAttribution is one frozen mapping row: what an ad meant at the moment vlab
// created it.
//
// Metadata is a snapshot, never a pointer at the current study conf. Study
// confs mutate, so a stratum's metadata today is not what it was when the ad
// was created — which is why resolving a respondent means reading this row and
// not re-reading the conf, even for an ad that is still live.
type AdAttribution struct {
	AdID     string
	Network  string
	Stratum  string
	Metadata map[string]json.RawMessage
}

// AdAttributions indexes a study's mapping rows by ad id.
//
// Keyed by ad id alone, not by (network, ad_id), even though that pair is the
// table's primary key. Meta ad ids are globally unique, this map is loaded for
// one study at a time, and keying on the pair would mean a respondent whose
// event carries an unrecognised platform (and therefore an empty network) fails
// to resolve against a row that is sitting right there. When a second ad network
// genuinely exists, this becomes a composite key and the tests below will say so.
type AdAttributions map[string]AdAttribution

// GetAdAttributions loads one study's mapping.
//
// Per-study rather than global, deliberately: it is cheaper, and an ad id
// belonging to another study then misses the lookup instead of silently
// importing a foreign study's strata. That miss is correct behaviour and is
// counted as `unmapped` by adAttributionOutcome.
//
// Deliberately unfiltered by whether the ad still exists on Facebook.
// Reconciliation deletes ads that fall out of the desired set, but respondents
// keep arriving from deleted ads — reshared page posts persist indefinitely —
// so a row must outlive its ad.
func GetAdAttributions(pool *pgxpool.Pool, study string) (AdAttributions, error) {
	attributions := AdAttributions{}

	q := `
        SELECT ad_id, network, stratum_id, metadata
        FROM ad_attributions
        WHERE study_id = $1
        `

	rows, err := pool.Query(context.Background(), q, study)
	if err != nil {
		return attributions, err
	}
	defer rows.Close()

	for rows.Next() {
		var a AdAttribution
		if err := rows.Scan(&a.AdID, &a.Network, &a.Stratum, &a.Metadata); err != nil {
			return attributions, err
		}
		attributions[a.AdID] = a
	}

	return attributions, rows.Err()
}
