"""`adopt/confs.py` is the one definition of the nine conf types. These are the
tests that stop it becoming the fifth.

Before it, the nine were listed in four places — the POST routes, the
whole-study validator, the schema export and the SDK — with a check between
exactly one pair of them. Each test here pins `confs.py` against one of the
others, so adding a tenth conf type fails until every consumer knows about it,
and nothing needs a database to say so.
"""

from datetime import datetime
from typing import Any, List

import orjson

from .confs import (
    CONF_TYPE_BY_URL_SEGMENT,
    CONF_TYPES,
    URL_SEGMENT_BY_CONF_TYPE,
    conf_type_for_url_segment,
    dump_conf,
    stored_conf,
)
from .study_conf import CreativeConf, GeneralConf, SimpleRecruitment
from .test_schema_export import _routes_declared_in_server

# ---------------------------------------------------------------------------
# The nine, against everything that lists them
# ---------------------------------------------------------------------------


def test_the_conf_types_are_exactly_the_post_routes():
    """Walks the real `@app.post(".../confs/<segment>")` decorators.

    The routes are the authority: they decide both the URL segment and the
    `conf_type` string written to `study_confs`. If a route is added and
    `CONF_TYPES` is not, the SDK silently drops that section on a pull/push
    round trip and the validator never reports it missing.
    """
    segments = set(_routes_declared_in_server())

    assert segments == set(URL_SEGMENT_BY_CONF_TYPE.values()), (
        "adopt/confs.py:CONF_TYPES has drifted from the POST routes in "
        "adopt/adopt/server/server.py."
    )


def test_the_url_segments_round_trip():
    for conf_type in CONF_TYPES:
        segment = URL_SEGMENT_BY_CONF_TYPE[conf_type]
        assert conf_type_for_url_segment(segment) == conf_type


def test_only_the_two_hyphenated_types_need_translating():
    """The trap this mapping exists for, stated as a test: `data-sources` and
    `inference-data` are the only two whose URL and storage names differ, and
    that difference cost a bug (plan §11.4 item 5)."""
    assert CONF_TYPE_BY_URL_SEGMENT == {
        "data-sources": "data_sources",
        "inference-data": "inference_data",
    }


def test_an_unknown_segment_passes_through():
    """The GET route accepts either spelling and lets the query miss; an
    unknown conf type is not this function's error to report."""
    assert conf_type_for_url_segment("nonsense") == "nonsense"


def test_the_validator_covers_exactly_the_conf_types():
    from .authoring.validate import SECTION_MODELS, SECTIONS

    assert tuple(SECTION_MODELS) == CONF_TYPES
    assert SECTIONS == CONF_TYPES


def test_the_schema_export_covers_exactly_the_conf_types():
    from .schema_export import CONF_ENDPOINTS

    exported = [conf_type_for_url_segment(ep.conf_type) for ep in CONF_ENDPOINTS]
    assert tuple(exported) == CONF_TYPES


def test_the_sdk_owns_no_list_of_its_own():
    from .sdk.study import PUSH_ORDER, SECTION_URL_SEGMENTS, SECTIONS

    assert SECTIONS is CONF_TYPES
    assert SECTION_URL_SEGMENTS is URL_SEGMENT_BY_CONF_TYPE
    # `push` deliberately writes in a DIFFERENT order (references first,
    # recruitment last), which is content rather than duplication -- but it has
    # to be the same nine.
    assert sorted(PUSH_ORDER) == sorted(CONF_TYPES)


# ---------------------------------------------------------------------------
# The storage transform, which is the one the SDK's diff normalises against
# ---------------------------------------------------------------------------


def _general() -> GeneralConf:
    return GeneralConf(
        name="x",
        credentials_key="Facebook",
        credentials_entity="facebook",
        ad_account="123",
        opt_window=48,
    )


def test_dump_conf_handles_both_an_object_and_a_list_section():
    """Six of the nine take a JSON array and three take an object; POSTing the
    wrong one is a 422, so the split is real and `dump_conf` carries it."""
    assert isinstance(dump_conf(_general()), dict)

    creatives: List[Any] = [
        CreativeConf(name="a", destination="d", template={"actor_id": "1"})
    ]
    dumped = dump_conf(creatives)
    assert isinstance(dumped, list) and len(dumped) == 1


def test_dump_conf_is_what_create_conf_used_to_inline():
    """The extraction was behaviour-preserving. This is the code it replaced."""
    creatives = [CreativeConf(name="a", destination="d", template={})]
    assert dump_conf(creatives) == [c.model_dump() for c in creatives]
    assert dump_conf(_general()) == _general().model_dump()


def test_stored_conf_is_dump_conf_through_the_drivers_orjson():
    """`db.create_study_conf` does `orjson.dumps(dat)`. `stored_conf` is that,
    read back — so a caller comparing against a stored row is comparing against
    the real transform rather than an approximation of it."""
    conf = _general()
    assert stored_conf(conf) == orjson.loads(orjson.dumps(dump_conf(conf)))


def test_stored_conf_renders_a_datetime_the_way_the_database_holds_it():
    """The case that makes the orjson round trip load-bearing rather than
    decorative: `model_dump()` leaves a `datetime` object, and a diff comparing
    that against the ISO string `GET /confs` returns would report every
    recruitment conf as changed from itself, forever, into a table with no
    delete."""
    conf = SimpleRecruitment(
        ad_campaign_name="hpv",
        objective="OUTCOME_ENGAGEMENT",
        optimization_goal="LINK_CLICKS",
        min_budget=100,
        budget=10000,
        max_sample=1000,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 3, 1),
    )

    assert isinstance(dump_conf(conf)["start_date"], datetime)
    assert stored_conf(conf)["start_date"] == "2026-01-01T00:00:00"


def test_stored_conf_fills_the_defaults_a_caller_omitted():
    """The other half of why a diff cannot compare against the request body.

    `_general()` never mentions `extra_metadata`; the stored row has it.
    """
    assert stored_conf(_general())["extra_metadata"] == {}


# ---------------------------------------------------------------------------
# The boundary the sharing must not cross
# ---------------------------------------------------------------------------


def test_the_sdk_does_not_import_the_server_package():
    """Sharing goes as far as `adopt.confs`, `adopt.study_conf` and
    `adopt.authoring` — and stops there.

    `adopt.server.*` pulls in FastAPI, psycopg and the Meta SDK, and the SDK is
    a CLIENT: it is installed with pipx on a laptop, it must import without a
    database driver being usable, and it must not grow a dependency on code
    that only ever runs inside the service. The tempting violation is the Meta
    error shape, which `server/meta.py` builds as a dict literal and
    `sdk/client.py` renders — six key names, documented in
    `documentation/agent-api.md` §2.5, which both follow. Importing the server
    to share six strings would cost the SDK the whole server dependency tree.

    Static, not `sys.modules`: the test suite imports the server app for its
    own fixtures, so a runtime check would pass vacuously.
    """
    import ast
    from pathlib import Path

    sdk_dir = Path(__file__).resolve().parent / "sdk"
    offenders = []

    for path in sorted(sdk_dir.glob("*.py")):
        if path.name.startswith("test_"):
            continue  # the tests DO drive the real app; that is the point
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = ("." * node.level) + (node.module or "")
                if "server" in module.split("."):
                    offenders.append(f"{path.name}: from {module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("adopt.server"):
                        offenders.append(f"{path.name}: import {alias.name}")

    assert offenders == [], offenders
