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
// Ad attribution splits three ways, and only one of the three is a bug:
//
//   - organic (no ref token) is the expected outcome for a respondent who
//     arrived without clicking an ad. It is worth *counting* — a study whose
//     organic share suddenly jumps has a leaked shortcode — but it must not
//     alarm, so it is a warning like the unmapped-source case.
//   - unmapped (token present, no mapping row) is always a bug: vlab created an
//     ad and failed to record what it meant, and every respondent it recruits
//     is silently dropped from stratum counts. This is the one case that gets
//     severity "error", which sorts it above warnings in the dashboard's
//     study-errors derivation (adopt/adopt/server/db.py).
//
// It is self-closing either way. The dashboard derivation keeps only events
// seen in the last 90 minutes, so once a missing mapping row is inserted and
// the next run stops emitting the error, it ages out on its own.
func classifyExtractionError(entity string) (eventType, severity string) {
	switch {
	case strings.HasPrefix(entity, "source="), entity == entityAdOrganic:
		return eventExtractionWarning, severityWarning
	case entity == entityAdUnmapped:
		return eventExtractionError, severityError
	default:
		// Unchanged from before: other extraction failures are errors by type
		// but were only ever recorded at warning severity.
		return eventExtractionError, severityWarning
	}
}
