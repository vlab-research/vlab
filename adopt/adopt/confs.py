"""The nine configuration sections: their names, their URLs, and how they store.

ONE DEFINITION, FOUR CONSUMERS

Before this module the nine conf types were listed in four places, each for a
different reason and each free to drift:

* `server/server.py` — nine `@app.post` routes, which are the authority for the
  URL segment and for the `conf_type` written to the database;
* `authoring/validate.py` — `SECTION_MODELS`, keyed by the STORED name;
* `schema_export.py` — `CONF_ENDPOINTS`, keyed by the URL segment;
* `sdk/study.py` — the study file's section keys and the POST paths.

Only the first three had any check between them (`test_schema_export.py`'s
route walker), and it covered exactly one pair. Adding a tenth conf type meant
finding four lists. They now all read from here, and `test_confs.py` walks the
real routes to prove this module has not drifted from them.

THE TWO SPELLINGS, WHICH ARE A REAL TRAP

Two of the nine are hyphenated in the URL and underscored in the database: you
POST to `.../confs/data-sources` and the row is `conf_type = 'data_sources'`.
That cost a bug — `GET /confs/data-sources` matched no row and raised, so until
adopt v0.1.85 the URL that could write those two sections was the one URL that
could not read them back (plan §11.4 item 5). Keeping both directions of the
mapping in one place, next to the list they are a mapping of, is how that stops
being something each caller rediscovers.

WHAT "STORED" MEANS

`create_conf` does not store your request body. It stores `model_dump()` of the
parsed model, which the driver then serialises with `orjson`. So the row holds
neither what you sent (unknown keys are gone, defaults are filled in) nor quite
what `model_dump()` returned (datetimes have become ISO strings). `stored_conf`
is that whole transform, in one place, so that a client wanting to know "what
will the server hold if I POST this?" — which is exactly what `vlab diff` asks
— gets the answer by *running the server's code*, not by reimplementing it.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import orjson

# The nine, keyed and ordered as they are STORED — the `study_confs.conf_type`
# value, which is also the key `GET /confs` returns and the key
# `validate_study` takes. Canonical rather than alphabetical order: it is the
# order of `documentation/agent-api.md` §3 and of the dashboard's own tabs.
CONF_TYPES: Tuple[str, ...] = (
    "general",
    "recruitment",
    "destinations",
    "creatives",
    "audiences",
    "variables",
    "strata",
    "data_sources",
    "inference_data",
)

# Stored name -> the URL segment that writes it. Seven are identical; the
# mapping exists for the two that are not.
URL_SEGMENT_BY_CONF_TYPE: Dict[str, str] = {
    name: name.replace("_", "-") for name in CONF_TYPES
}

# The inverse, restricted to the two that differ — which is the form the GET
# route wants, since it accepts either spelling and falls back to the segment
# it was given. Both directions live here so neither can be rederived wrongly.
CONF_TYPE_BY_URL_SEGMENT: Dict[str, str] = {
    segment: name
    for name, segment in URL_SEGMENT_BY_CONF_TYPE.items()
    if segment != name
}


def conf_type_for_url_segment(segment: str) -> str:
    """The stored `conf_type` for a URL segment, or the segment unchanged.

    Unknown segments pass through rather than raising: the GET route accepts
    both spellings and lets the query miss, and an unknown conf type is not
    this function's error to report.
    """
    return CONF_TYPE_BY_URL_SEGMENT.get(segment, segment)


def dump_conf(config: Any) -> Any:
    """`model_dump()` of one whole section — what `create_conf` hands the driver.

    Takes a parsed model, or a list of them for the six array-valued sections.
    The list/object split is the section's own: POSTing a bare object to
    `/confs/creatives` is a 422 and always was.
    """
    if isinstance(config, list):
        return [c.model_dump() for c in config]
    return config.model_dump()


def json_safe(value: Any) -> Any:
    """A JSON-shaped copy of arbitrary conf data, through the driver's orjson.

    Not the same job as `stored_conf`, which starts from a parsed model. This
    starts from whatever a caller is holding -- a section read out of a YAML
    file, say -- and answers "what will this look like once it has been through
    a JSON serialiser", WITHOUT dropping anything the models do not declare.

    The case it exists for: YAML 1.1 parses an unquoted `start_date:
    2026-06-01` into a `datetime.date`. pydantic accepts that happily, so
    `validate` passes and `diff` is clean, and then the POST dies inside the
    HTTP library with "Object of type date is not JSON serializable" -- a
    local encoding failure that looks like the network. orjson serialises dates
    and datetimes natively, and it is the same serialiser the database driver
    uses, so a value put through here is a value the server will accept and
    store unchanged.

    Preserving undeclared keys is the point of doing this rather than posting
    `stored_conf` of the parsed section: a misspelled field has to survive as
    far as the server, so that the 422 names it. Silently dropping it here
    would be the `extra="ignore"` failure all over again, moved client-side.
    """
    return orjson.loads(orjson.dumps(value))


def stored_conf(config: Any) -> Any:
    """What `study_confs.conf` will actually hold, as JSON-shaped Python.

    `dump_conf` put through the same `orjson` the driver uses
    (`db.create_study_conf`) and read back. The round trip is not decoration:
    it is what turns a `datetime` into `"2026-01-01T00:00:00"`, and doing it
    here rather than trusting pydantic's `mode="json"` to agree with orjson
    means a caller comparing against a stored conf is comparing against the
    real transform instead of a close approximation of it.

    This is the function `vlab diff` normalises with. If `create_conf` ever
    changes what it stores, the diff follows it, because there is one
    definition rather than two.
    """
    return json_safe(dump_conf(config))
