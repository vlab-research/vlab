package main

// study_run_events writer — see planning/study-errors-surfacing.md.
// The event log is display/audit only (never gating); writes are best-effort
// and must never interrupt the run's primary work (inference aggregation).

import (
	"context"
	"encoding/json"
	"log"
	"strings"

	"github.com/jackc/pgx/v4/pgxpool"
)

const (
	sourceInference = "inference"

	eventRunStarted        = "run_started"
	eventRunOK             = "run_ok"
	eventRunError          = "run_error"
	eventExtractionError   = "extraction_error"
	eventExtractionWarning = "extraction_warning"

	severityError   = "error"
	severityWarning = "warning"

	// All study-level swoosh failures share one fingerprint so a single run_ok
	// (same fingerprint) closes whichever failure was latest in the derivation.
	fingerprintRun      = "inference:run"
	fingerprintExPrefix = "inference:extraction:"
)

// RecordEvent inserts one immutable fact into study_run_events. Best-effort:
// failures are logged and swallowed — the run's primary work is inference,
// not event-logging.
func RecordEvent(pool *pgxpool.Pool, studyID, source, runID, eventType, fingerprint, severity, message string, details map[string]interface{}) {
	q := `
        INSERT INTO study_run_events
            (study_id, source, run_id, event_type, fingerprint, severity, message, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`

	var detailsJSON []byte
	if details != nil {
		var err error
		detailsJSON, err = json.Marshal(details)
		if err != nil {
			log.Printf("study_run_events: could not marshal details for %s/%s: %v", studyID, eventType, err)
			detailsJSON = nil
		}
	}

	_, err := pool.Exec(context.Background(), q, studyID, source, runID, eventType, fingerprint, severity, message, detailsJSON)
	if err != nil {
		log.Printf("study_run_events: could not record %s for study %s: %v", eventType, studyID, err)
	}
}

// recordRunOutcome is the convenience wrapper for the run-level facts
// (run_ok / run_error) that open and close the shared run fingerprint.
func recordRunOutcome(pool *pgxpool.Pool, studyID, runID, eventType, severity, message, stage string) {
	var details map[string]interface{}
	if stage != "" {
		details = map[string]interface{}{"stage": stage}
	}
	RecordEvent(pool, studyID, sourceInference, runID, eventType, fingerprintRun, severity, message, details)
}

// recordExtractionError maps one aggregated ExtractionError to an
// extraction_warning (unmapped source) or extraction_error (other extraction
// failure) event. Fingerprint is per-entity so a run_ok does NOT close it —
// fixed extraction problems age out via the recency predicate instead.
func recordExtractionError(pool *pgxpool.Pool, studyID, runID string, e ExtractionError) {
	eventType, severity := classifyExtractionError(e.Entity)

	details := map[string]interface{}{
		"entity":         e.Entity,
		"count":          e.Count,
		"sample_message": e.Message,
	}
	for k, v := range e.Details {
		details[k] = v
	}

	RecordEvent(pool, studyID, sourceInference, runID, eventType,
		fingerprintExPrefix+e.Entity, severity, e.Message, details)
}

// classifyExtractionError decides how loudly one aggregated extraction problem
// is surfaced, from its entity key alone.
//
// unmapped (a ref token with no mapping row) is a WARNING, and used to be an
// error. The reasoning for "error" was that it is always a bug -- vlab created
// an ad and failed to record what it meant. That covers one of the two causes.
//
// The other is ordinary: a token that belongs to a *different* study. Studies
// that share a survey shortcode see each other's respondents, and the lookup is
// per study precisely so a foreign token misses rather than silently importing
// another study's strata (GetAdAttributions). That miss is the mechanism
// working. It also never stops -- as long as the two studies share the survey,
// every run re-emits it -- and an error that can never be cleared stops being
// read as one, burying the errors that can.
//
// Warning does not mean hidden: the dashboard's derivation
// (adopt/adopt/server/db.py) keeps warnings and sorts them below errors, which
// is exactly the intended demotion.
//
// The cost is real and accepted: a genuinely lost mapping row -- the failure
// that emptied ad_attributions across all of production on 2026-08-30 -- now
// reports at the same level as a shared dataset. Two things carry that weight
// instead. malaria.heal_ad_attributions repairs it on the next run rather than
// leaving it permanent, and adopt/scripts/write_path_probe.py is the
// purpose-built check that compares Meta's ads against the table.
//
// Either way it is self-closing: the derivation keeps only events seen in the
// last 90 minutes, so once the row exists and the next run stops emitting, it
// ages out on its own.
//
// Kept as an explicit case rather than folded into the default it now matches,
// so that a future change to the default cannot silently re-classify this.
func classifyExtractionError(entity string) (eventType, severity string) {
	switch {
	case strings.HasPrefix(entity, "source="):
		return eventExtractionWarning, severityWarning
	case entity == entityAdUnmapped:
		return eventExtractionError, severityWarning
	default:
		// Unchanged from before: other extraction failures are errors by type
		// but were only ever recorded at warning severity.
		return eventExtractionError, severityWarning
	}
}
