"""Ad-ID attribution: the mapping row, end to end (A1 + A2).

vlab is taking over the ad -> stratum join from the dotted ref string that used
to ride to the survey platform inside every message. The join only works if a
row lands in `ad_attributions` for every ad vlab creates, exactly once, frozen
at creation, and never removed.

The failure mode these tests exist to prevent is quiet: a missing or wrong row
does not raise, it attributes a respondent to no stratum. Recruitment then
looks incomplete while the optimizer reallocates budget away from a stratum
that is in fact recruiting fine. There is deliberately no backfill path -- the
design rejected retrofitting existing studies -- so a row that is not written
at creation is lost for good.

These are integration tests against the real CockroachDB test instance. Run
`make test-db` in adopt/ first.
"""

import json
from unittest.mock import patch

import pytest
from test.dbfix import _reset_db, cnf

from .campaign_queries import create_ad_attribution, get_ad_attributions
from .db import execute, query
from .facebook.update import Instruction, created_id
from .malaria import run_instructions

STUDY_ID = "00000000-0000-0000-0000-0000000000aa"
OTHER_STUDY_ID = "00000000-0000-0000-0000-0000000000bb"


def _provenance(
    study_id=STUDY_ID,
    stratum_id="stratum-1",
    creative_name="Smiling",
    shortcode="mnchweek",
    metadata=None,
):
    """A provenance dict shaped exactly as marketing.ad_provenance builds one.

    `metadata` defaults to the full ref-equivalent blob -- note `creative` and
    `form`, which are the two keys that would be missing if anyone froze
    `stratum.metadata` instead. See test_marketing for the invariant itself.
    """
    return {
        "study_id": study_id,
        "stratum_id": stratum_id,
        "creative_name": creative_name,
        "shortcode": shortcode,
        "metadata": metadata
        if metadata is not None
        else {
            "creative": creative_name,
            "form": shortcode,
            "gender": "women",
            "Age": "Like Parents",
        },
        "resolved_from": "ad_id",
    }


def _ad_create(provenance=None, name="Smiling"):
    return Instruction(
        "ad",
        "create",
        {"adset_id": "adset-id", "name": name, "status": "ACTIVE"},
        None,
        provenance,
    )


class FakeUpdater:
    """Stands in for GraphUpdater.

    Everything under test happens *after* Facebook answers, so the Facebook
    half is replaced wholesale rather than mocked at the SDK level. `results`
    is consumed one entry per instruction: a string is the id Facebook
    returned, None means it returned no id, and an exception instance is
    raised as the create failing.
    """

    def __init__(self, results):
        self.results = list(results)
        self.executed = []

    def execute(self, instruction):
        self.executed.append(instruction)
        res = self.results.pop(0) if self.results else None

        if isinstance(res, BaseException):
            raise res

        return ({"instruction": {"node": instruction.node}}, res)


def _run(instructions, results):
    """run_instructions with the Graph API replaced. Returns the fake updater."""
    fake = FakeUpdater(results)
    with patch("adopt.malaria.GraphUpdater", lambda state: fake):
        run_instructions(instructions, state=None, db_conf=cnf)
    return fake


def _all_rows():
    q = """
    SELECT network, ad_id, study_id, stratum_id, creative_name,
           shortcode, metadata, resolved_from
    FROM ad_attributions
    ORDER BY created
    """
    return list(query(cnf, q, (), as_dict=True))


# ---------------------------------------------------------------------------
# The happy path, through run_instructions
# ---------------------------------------------------------------------------


def test_successful_ad_create_writes_exactly_one_correct_row():
    _reset_db()
    prov = _provenance()

    _run([_ad_create(prov)], ["120254866237980150"])

    rows = _all_rows()
    assert len(rows) == 1

    row = rows[0]
    assert row["network"] == "facebook"
    assert row["ad_id"] == "120254866237980150"
    assert str(row["study_id"]) == STUDY_ID
    assert row["stratum_id"] == "stratum-1"
    assert row["creative_name"] == "Smiling"
    assert row["shortcode"] == "mnchweek"
    assert row["resolved_from"] == "ad_id"

    # The whole point: the frozen blob survives the JSONB round trip intact,
    # including `creative` and `form`.
    assert row["metadata"] == prov["metadata"]


def test_several_ad_creates_write_one_row_each_keyed_on_their_own_id():
    _reset_db()

    _run(
        [
            _ad_create(_provenance(stratum_id="s1", creative_name="Smiling")),
            _ad_create(_provenance(stratum_id="s2", creative_name="Serious")),
        ],
        ["ad-1", "ad-2"],
    )

    rows = {r["ad_id"]: r for r in _all_rows()}
    assert set(rows) == {"ad-1", "ad-2"}
    assert rows["ad-1"]["stratum_id"] == "s1"
    assert rows["ad-2"]["stratum_id"] == "s2"


# ---------------------------------------------------------------------------
# Nothing else writes a row
# ---------------------------------------------------------------------------


def test_failed_ad_create_writes_no_row():
    """No ad, no row. A row for an ad that does not exist would be worse than
    none: it would look like attribution coverage that isn't there."""
    _reset_db()

    with pytest.raises(RuntimeError):
        _run([_ad_create(_provenance())], [RuntimeError("facebook said no")])

    assert _all_rows() == []


def test_ad_create_without_provenance_writes_no_row():
    """The single-instruction server endpoint creates ads this way.

    Nothing is known about the stratum, so there is nothing truthful to write.
    """
    _reset_db()

    _run([_ad_create(provenance=None)], ["ad-1"])

    assert _all_rows() == []


def test_ad_create_that_returns_no_id_writes_no_row_and_does_not_raise():
    """A create that succeeds but yields no id cannot be mapped.

    Logged loudly rather than raised: the ad exists, so aborting would not
    undo anything, and the miss surfaces later as an unmapped-ad count.
    """
    _reset_db()

    _run([_ad_create(_provenance())], [None])

    assert _all_rows() == []


def test_non_ad_creates_write_no_row():
    """Adsets, campaigns and audiences all return ids. None of them are ads."""
    _reset_db()

    _run(
        [
            Instruction("adset", "create", {"name": "stratum-1"}, None),
            Instruction("campaign", "create", {"name": "campaign"}, None),
            Instruction("custom_audience", "create", {"name": "aud"}, None),
        ],
        ["adset-1", "campaign-1", "aud-1"],
    )

    assert _all_rows() == []


def test_ad_updates_and_deletes_write_no_row():
    _reset_db()

    _run(
        [
            Instruction("ad", "update", {"status": "PAUSED"}, "ad-1"),
            Instruction("ad", "delete", {}, "ad-1"),
        ],
        [None, None],
    )

    assert _all_rows() == []


# ---------------------------------------------------------------------------
# Invariant 2: append-only
# ---------------------------------------------------------------------------


def test_deleting_the_ad_leaves_its_mapping_row_intact():
    """The invariant reconciliation is most likely to violate.

    Reconciliation deletes ads that fall out of the desired set, but
    respondents keep arriving from deleted ads -- CTWA referrals carry
    ads_context_data.post_id and page posts persist and can be reshared
    indefinitely. The row has to outlive the ad, which is also why this table
    can never be rebuilt from live Facebook state.
    """
    _reset_db()
    _run([_ad_create(_provenance())], ["ad-1"])
    assert len(_all_rows()) == 1

    # A later reconciliation run drops the ad.
    _run([Instruction("ad", "delete", {}, "ad-1")], [None])

    rows = _all_rows()
    assert len(rows) == 1
    assert rows[0]["ad_id"] == "ad-1"


def test_row_survives_deletion_of_its_study():
    """No FK, therefore no cascade -- deliberately.

    A cascading delete is still a delete path, and this table has none. The
    row is evidence about an ad that ran, and it stays true after the study
    record is gone.
    """
    _reset_db()
    execute(
        cnf,
        "INSERT INTO users(id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
        ["test@email.com"],
    )
    res = query(
        cnf,
        "INSERT INTO studies(user_id, name, slug) VALUES (%s, %s, %s) RETURNING id",
        ["test@email.com", "a-study", "a-study"],
    )
    study_id = str(list(res)[0][0])

    create_ad_attribution("ad-1", _provenance(study_id=study_id), cnf)
    assert len(_all_rows()) == 1

    execute(cnf, "DELETE FROM studies WHERE id = %s", [study_id])

    rows = _all_rows()
    assert len(rows) == 1
    assert str(rows[0]["study_id"]) == study_id


# ---------------------------------------------------------------------------
# Invariant 3: frozen at creation, and therefore idempotent
# ---------------------------------------------------------------------------


def test_rerunning_reconciliation_neither_duplicates_nor_mutates():
    """Re-running must be free.

    In practice reconciliation emits no create for an ad that already exists,
    so this is belt and braces -- but the belt matters, because the write is
    the only thing standing between a conf edit and a rewritten snapshot.
    """
    _reset_db()
    original = _provenance()

    _run([_ad_create(original)], ["ad-1"])
    _run([_ad_create(original)], ["ad-1"])

    rows = _all_rows()
    assert len(rows) == 1
    assert rows[0]["metadata"] == original["metadata"]


def test_a_later_write_cannot_overwrite_the_frozen_metadata():
    """Study confs mutate; the row must not follow them.

    A stratum's metadata today is not what it was when the ad was created, so
    even a live ad cannot be resolved by reading the current conf. The row is
    a snapshot, not a pointer -- ON CONFLICT DO NOTHING is that sentence made
    mechanical.
    """
    _reset_db()
    original = _provenance(metadata={"creative": "Smiling", "gender": "women"})
    edited = _provenance(
        stratum_id="renamed-stratum",
        metadata={"creative": "Smiling", "gender": "men"},
    )

    assert create_ad_attribution("ad-1", original, cnf) is not None
    # The second write is refused, and says so by returning None.
    assert create_ad_attribution("ad-1", edited, cnf) is None

    rows = _all_rows()
    assert len(rows) == 1
    assert rows[0]["metadata"] == {"creative": "Smiling", "gender": "women"}
    assert rows[0]["stratum_id"] == "stratum-1"


# ---------------------------------------------------------------------------
# The key: (network, ad_id)
# ---------------------------------------------------------------------------


def test_the_same_id_on_two_networks_is_two_rows():
    """`network` is the discriminator, added before the second network exists.

    Meta ad ids live in Meta's namespace; TikTok and Google Ads are already
    contemplated. It is also the ad *network*, not the messaging channel --
    Messenger and WhatsApp ads are both 'facebook'.
    """
    _reset_db()

    create_ad_attribution("shared-id", _provenance(stratum_id="s1"), cnf)
    create_ad_attribution(
        "shared-id", _provenance(stratum_id="s2"), cnf, network="tiktok"
    )

    rows = {r["network"]: r for r in _all_rows()}
    assert set(rows) == {"facebook", "tiktok"}
    assert rows["facebook"]["stratum_id"] == "s1"
    assert rows["tiktok"]["stratum_id"] == "s2"


def test_network_defaults_to_facebook():
    _reset_db()
    create_ad_attribution("ad-1", _provenance(), cnf)
    assert _all_rows()[0]["network"] == "facebook"


# ---------------------------------------------------------------------------
# Reading it back
# ---------------------------------------------------------------------------


def test_get_ad_attributions_returns_only_the_requested_study():
    """Per-study, so an ad id from another study misses rather than silently
    importing foreign strata."""
    _reset_db()
    create_ad_attribution("ad-1", _provenance(study_id=STUDY_ID), cnf)
    create_ad_attribution("ad-2", _provenance(study_id=OTHER_STUDY_ID), cnf)

    rows = get_ad_attributions(STUDY_ID, cnf)
    assert [r["ad_id"] for r in rows] == ["ad-1"]
    assert rows[0]["metadata"]["creative"] == "Smiling"


def test_shortcode_is_nullable_for_destinations_that_have_none():
    """Web and app destinations route via their URL/deeplink, not a shortcode."""
    _reset_db()
    create_ad_attribution("ad-1", _provenance(shortcode=None), cnf)

    rows = _all_rows()
    assert rows[0]["shortcode"] is None


def test_metadata_survives_unicode_and_punctuation():
    """The blob is JSONB, not a dotted string, so it has no escaping grammar
    to get wrong. Values with dots in particular are mangled by make_ref and
    are preserved here -- see test_marketing."""
    _reset_db()
    md = {"creative": "Ad — 1", "city": "St. Louis", "note": "a.b/c?d=e", "q": "ë"}
    create_ad_attribution("ad-1", _provenance(metadata=md), cnf)

    assert _all_rows()[0]["metadata"] == md


# ---------------------------------------------------------------------------
# Capturing the id at all
# ---------------------------------------------------------------------------


def test_created_id_reads_the_id_from_a_created_object():
    class _Created:
        def __init__(self, data):
            self._data = data

        def __getitem__(self, k):
            return self._data[k]

    assert created_id(_Created({"id": "120254866237980150"})) == "120254866237980150"
    assert created_id({"id": 12345}) == "12345"


def test_created_id_is_none_when_there_is_nothing_to_read():
    """Defensive on purpose: a missing id must not crash a run that has
    already successfully created ads."""

    class _NoId:
        def __getitem__(self, k):
            raise KeyError(k)

    assert created_id(None) is None
    assert created_id({}) is None
    assert created_id(_NoId()) is None


def test_a_write_failure_stops_the_run_rather_than_creating_unmappable_ads():
    """Fail fast and loud.

    An ad that exists on Facebook with no mapping row can never be attributed,
    and there is no backfill. Stopping leaves the remaining ads uncreated,
    which the next run fixes; carrying on would mint permanent silent gaps.
    """
    _reset_db()
    instructions = [_ad_create(_provenance(), name="a"), _ad_create(_provenance(), name="b")]

    with patch(
        "adopt.malaria.create_ad_attribution",
        side_effect=RuntimeError("db is down"),
    ):
        with pytest.raises(RuntimeError, match="db is down"):
            _run(instructions, ["ad-1", "ad-2"])

    assert _all_rows() == []
