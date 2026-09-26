"""adopt's side of study_run_events: what a cron run says about each study.

Pure functions decide which facts a run produces and how an exception reads to
a study owner; `record_events` is the only function here that does IO. The
table, the derivation that reads it and the per-source recency windows are
described in adopt/README.md, "Study run events".
"""

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, Sequence, Tuple

from facebook_business.exceptions import FacebookRequestError

from .db import execute

SOURCE_INFERENCE = "inference"
SOURCE_OPTIMIZER_ADS = "optimizer:ads"
SOURCE_OPTIMIZER_AUDIENCE = "optimizer:audience"
SOURCE_OPTIMIZER_RECRUITMENT_DATA = "optimizer:recruitment_data"

EVENT_RUN_STARTED = "run_started"
EVENT_RUN_OK = "run_ok"
EVENT_RUN_ERROR = "run_error"

SEVERITY_ERROR = "error"

STAGE_LOAD = "load"
STAGE_PLAN = "plan"
STAGE_EXECUTE = "execute"
STAGE_HEAL = "heal"

STAGE_LABELS = {
    STAGE_LOAD: "Could not load the study's configuration",
    STAGE_PLAN: "Could not work out what to change on Facebook",
    STAGE_EXECUTE: "Facebook refused a change",
    STAGE_HEAL: "Could not record the ads this run created",
}

# The longest cron period any committed devops/values/*.yaml gives each
# writer. A deployment's schedule is not visible to the reader, so the window
# is sized for the slowest environment; test_run_events checks every values
# file against this table so a slowed cron fails a test instead of flickering.
SOURCE_PERIODS = {
    SOURCE_INFERENCE: timedelta(hours=1),
    SOURCE_OPTIMIZER_ADS: timedelta(hours=4),
    SOURCE_OPTIMIZER_AUDIENCE: timedelta(hours=4),
    SOURCE_OPTIMIZER_RECRUITMENT_DATA: timedelta(hours=4),
}

# Three periods, so one slow or skipped run does not resolve an error that is
# still true.
RUNS_PER_WINDOW = 3

DEFAULT_WINDOW = timedelta(minutes=90)

# Long enough for any message adopt writes itself; the bound exists for
# third-party exceptions whose text is a dump rather than a sentence.
MAX_MESSAGE_CHARS = 4000


@dataclass(frozen=True)
class RunEvent:
    study_id: str
    source: str
    run_id: str
    event_type: str
    fingerprint: str = ""
    severity: str = ""
    message: str = ""
    details: Optional[Dict[str, Any]] = None


def run_fingerprint(source: str) -> str:
    """One fingerprint per source, shared by run_ok and run_error.

    Sharing it is what lets a healthy run close the latest failure, and keeping
    it free of anything volatile is what makes a refusal repeated every run one
    open error rather than a new one each time.
    """
    return f"{source}:run"


def run_started(study_id: str, source: str, run_id: str) -> RunEvent:
    return RunEvent(study_id, source, run_id, EVENT_RUN_STARTED)


def run_ok(study_id: str, source: str, run_id: str) -> RunEvent:
    return RunEvent(
        study_id, source, run_id, EVENT_RUN_OK, fingerprint=run_fingerprint(source)
    )


def run_error(
    study_id: str, source: str, run_id: str, stage: str, exc: BaseException
) -> RunEvent:
    description, exc_details = describe_exception(exc)
    label = STAGE_LABELS.get(stage, f"Failed during {stage}")
    return RunEvent(
        study_id,
        source,
        run_id,
        EVENT_RUN_ERROR,
        fingerprint=run_fingerprint(source),
        severity=SEVERITY_ERROR,
        message=truncate(f"{label}: {description}"),
        details={"stage": stage, **exc_details},
    )


def describe_exception(exc: BaseException) -> Tuple[str, Dict[str, Any]]:
    """The sentence a study owner reads, and structured context for it.

    A FacebookRequestError's str() includes the request params, which can carry
    the access token, and it is shown to everyone who can open the study. So it
    is built from Meta's own error fields instead, never from str().
    """
    exception_name = type(exc).__name__

    if isinstance(exc, FacebookRequestError):
        return _describe_facebook_error(exc)

    text = str(exc).strip()
    description = text if text else exception_name
    return description, {"exception": exception_name}


def _describe_facebook_error(exc: FacebookRequestError) -> Tuple[str, Dict[str, Any]]:
    body = exc.body()
    error = body.get("error", {}) if isinstance(body, dict) else {}
    user_title = error.get("error_user_title")
    user_msg = error.get("error_user_msg")

    parts = [exc.api_error_message() or exc.get_message() or "request failed"]
    if user_title or user_msg:
        parts.append(": ".join(p for p in (user_title, user_msg) if p))
    description = " — ".join(parts)

    request = exc.request_context() or {}
    details = {
        "exception": type(exc).__name__,
        "http_status": exc.http_status(),
        "api_error_code": exc.api_error_code(),
        "api_error_subcode": exc.api_error_subcode(),
        "api_error_type": exc.api_error_type(),
        "is_transient": exc.api_transient_error(),
        "method": request.get("method"),
        "path": request.get("path"),
    }
    if exc.api_blame_field_specs():
        details["blame_field_specs"] = exc.api_blame_field_specs()

    return description, {k: v for k, v in details.items() if v is not None}


def truncate(message: str, limit: int = MAX_MESSAGE_CHARS) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 1] + "…"


def recency_window(source: str) -> timedelta:
    """How long an error from `source` stays open without being re-emitted."""
    period = SOURCE_PERIODS.get(source)
    if period is None:
        return DEFAULT_WINDOW
    return period * RUNS_PER_WINDOW


def max_recency_window() -> timedelta:
    return max([DEFAULT_WINDOW, *(recency_window(s) for s in SOURCE_PERIODS)])


def is_within_window(source: str, age: timedelta) -> bool:
    return age < recency_window(source)


def event_row(event: RunEvent) -> Tuple[Any, ...]:
    details = json.dumps(event.details) if event.details is not None else None
    return (
        event.study_id,
        event.source,
        event.run_id,
        event.event_type,
        event.fingerprint,
        event.severity,
        event.message,
        details,
    )


INSERT_EVENT = """
INSERT INTO study_run_events
    (study_id, source, run_id, event_type, fingerprint, severity, message, details)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def record_events(db_conf: str, events: Sequence[RunEvent]) -> bool:
    """Insert events, best-effort. Returns whether they were written.

    Never raises: the log is for display, and a run must not fail, or skip the
    next study, because its report about itself could not be stored. Callers
    log the underlying error themselves before calling this, so a failed write
    loses the dashboard copy and nothing else.
    """
    if not events:
        return True
    try:
        for event in events:
            execute(db_conf, INSERT_EVENT, event_row(event))
        return True
    except Exception as e:
        logging.warning(
            f"study_run_events: could not record {[ev.event_type for ev in events]} "
            f"for study {events[0].study_id}: {e}"
        )
        return False
