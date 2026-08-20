package main

// The read side of the ad -> stratum mapping vlab freezes at ad-creation time
// (adopt/adopt/campaign_queries.py:create_ad_attribution). See
// documentation/ad-attributions.md and planning/encoded-ref-attribution-plan.md.

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
//
// RefToken is the join key. AdID and Network are captured too, but are not
// joined on — see AdAttributions.
type AdAttribution struct {
	AdID     string
	Network  string
	Stratum  string
	Metadata map[string]json.RawMessage
	RefToken string
}

// AdAttributions holds a study's mapping rows, indexed by the one key that is
// joined on.
//
// ByRefToken is that index. The token rides the ref itself — a carrier vlab
// authors — so it reaches essentially every ad entrant, and a conf declaring
// `mapping: "ad_table_lookup"` names the metadata key it arrives under.
//
// There is deliberately **no ByAdID index**. ad_id was the earlier attempt at
// the same shape (opaque ad identifier -> frozen row -> stratum metadata) and
// is superseded, not wrong: on Messenger, Meta sends the referral webhook that
// carries it for only ~31% of ad entrants, so the other 69% could never be
// joined. The column is still selected and still on the struct — it is what
// the recruitment-health alerting gates on, and a platform that some day needs
// an id-carrier join could have it back in this same shape — but nothing joins
// on it, and adding a second index here would recreate exactly the runtime
// mechanism-selection the design forbids (see adAttributionOutcome).
//
// A struct with one index rather than a bare map, so that every call site reads
// `attributions.ByRefToken[token]` and says out loud which key it joined on.
type AdAttributions struct {
	ByRefToken map[string]AdAttribution
}

// NewAdAttributions returns an empty, usable mapping. The zero value's map is
// nil, which reads fine but cannot be written to.
func NewAdAttributions() AdAttributions {
	return AdAttributions{ByRefToken: map[string]AdAttribution{}}
}

// Len is the number of rows that can actually be joined on — reported in the
// unmapped error's details and logged per run, where "how many ads does this
// study have a token for" is the number that makes a miss diagnosable.
func (a AdAttributions) Len() int {
	return len(a.ByRefToken)
}

// GetAdAttributions loads one study's mapping.
//
// Per-study rather than global, deliberately: it is cheaper, and a token
// belonging to another study then misses the lookup instead of silently
// importing a foreign study's strata. That miss is correct behaviour and is
// counted as `unmapped` by adAttributionOutcome.
//
// Deliberately unfiltered by whether the ad still exists on Facebook.
// Reconciliation deletes ads that fall out of the desired set, but respondents
// keep arriving from deleted ads — reshared page posts persist indefinitely —
// so a row must outlive its ad.
//
// A NULL ref_token is the normal case and means something: that ad's ref
// carries no token because its destination is not in ref_mode "encoded". Such
// a row is loaded but not indexed — it has no join key, so there is nothing to
// index it under.
func GetAdAttributions(pool *pgxpool.Pool, study string) (AdAttributions, error) {
	attributions := NewAdAttributions()

	// ad_id is selected but not indexed: captured for monitoring, never joined.
	q := `
        SELECT ad_id, network, stratum_id, metadata, ref_token
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

		// ref_token is nullable, so it cannot be scanned straight into a string.
		var refToken *string

		if err := rows.Scan(&a.AdID, &a.Network, &a.Stratum, &a.Metadata, &refToken); err != nil {
			return attributions, err
		}

		if refToken != nil {
			a.RefToken = *refToken
		}

		if a.RefToken != "" {
			attributions.ByRefToken[a.RefToken] = a
		}
	}

	return attributions, rows.Err()
}
