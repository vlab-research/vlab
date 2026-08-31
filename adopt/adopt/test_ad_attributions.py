"""Ad-ID attribution: the mapping row.

vlab took the ad -> stratum join over from the dotted ref string that used to
ride to the survey platform inside every message. The join works only if
`ad_attributions` holds a row for every ad vlab has, once each, never removed.

The failure mode these tests exist to prevent is quiet: a missing or wrong row
does not raise, it attributes a respondent to no stratum. Recruitment then
looks incomplete while the optimizer reallocates budget away from a stratum
that is in fact recruiting fine.

**One writer.** `malaria.heal_ad_attributions` is the only thing that writes
here, and it works by reconciliation: read the ads that exist, write a row for
each that has none. There used to be a second writer that captured the ad id
out of Facebook's response to a create -- it wrote at the ideal moment but only
for ads it had made itself, so ads created any other way were unmapped forever.
That is the bug these tests were extended for; see the healing section.

These are integration tests against the real CockroachDB test instance. Run
`make test-db` in adopt/ first.
"""

import json
from datetime import datetime

import pytest
from test.dbfix import _reset_db, cnf

from .campaign_queries import create_ad_attribution, get_ad_attributions
from .db import execute, query
from .facebook.state import StateNameError
from .malaria import heal_ad_attributions
from .study_conf import (
    CreativeConf,
    FlyMessengerDestination,
    GeneralConf,
    SimpleRecruitment,
    StratumConf,
    StudyConf,
    UserInfo,
)

STUDY_ID = "00000000-0000-0000-0000-0000000000aa"
OTHER_STUDY_ID = "00000000-0000-0000-0000-0000000000bb"


def _provenance(
    study_id=STUDY_ID,
    stratum_id="stratum-1",
    creative_name="Smiling",
    shortcode="mnchweek",
    metadata=None,
    ref_token=None,
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
        "ref_token": ref_token,
    }


def _all_rows():
    q = """
    SELECT network, ad_id, study_id, stratum_id, creative_name,
           shortcode, metadata, resolved_from
    FROM ad_attributions
    ORDER BY created
    """
    return list(query(cnf, q, (), as_dict=True))


# ---------------------------------------------------------------------------
# The row outlives everything it refers to
# ---------------------------------------------------------------------------


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


def test_ref_token_round_trips_through_the_row():
    """The whole point of the column: what the ad ships must come back out.

    If it did not, every respondent from an encoded-ref ad would arrive carrying
    a token that matches no row and be counted unmapped -- for the entire study,
    and silently until someone read the counters.
    """
    _reset_db()
    create_ad_attribution("ad-1", _provenance(ref_token="a7f3c20b1e"), cnf)

    rows = get_ad_attributions(STUDY_ID, cnf)

    assert [r["ref_token"] for r in rows] == ["a7f3c20b1e"]


def test_a_row_without_a_token_stores_null_not_empty_string():
    """NULL means "this ad's ref carries no token", which is a fact about the ad.

    An empty string would be a value, and a value can be joined against -- so a
    respondent arriving with an empty token could match every unencoded ad in the
    study at once.
    """
    _reset_db()
    create_ad_attribution("ad-1", _provenance(), cnf)

    rows = get_ad_attributions(STUDY_ID, cnf)

    assert rows[0]["ref_token"] is None


def test_a_provenance_dict_predating_the_column_still_writes():
    """Written with .get rather than [], so an older caller is not a crash.

    Refusing the write would be strictly worse than an unattributable ad: the ad
    exists on Facebook either way, and a missing row cannot be recovered.
    """
    _reset_db()
    old_shape = _provenance()
    del old_shape["ref_token"]

    assert create_ad_attribution("ad-1", old_shape, cnf) is not None
    assert get_ad_attributions(STUDY_ID, cnf)[0]["ref_token"] is None


def test_the_token_is_frozen_like_everything_else_on_the_row():
    """Append-only applies to the token too.

    A re-run must not be able to rewrite it. If it could, a conf edit that
    changed a creative name would silently repoint an existing ad's token and
    orphan every respondent already attributed through the old one.
    """
    _reset_db()
    create_ad_attribution("ad-1", _provenance(ref_token="a7f3c20b1e"), cnf)
    create_ad_attribution("ad-1", _provenance(ref_token="ffffffffff"), cnf)

    rows = get_ad_attributions(STUDY_ID, cnf)

    assert len(rows) == 1
    assert rows[0]["ref_token"] == "a7f3c20b1e"


# ---------------------------------------------------------------------------
# Healing: the only writer
# ---------------------------------------------------------------------------
#
# The write used to happen at ad-creation time, from the id Facebook returned.
# That writer could only ever write for ads it had made itself, and
# reconciliation creates an ad once -- so an ad that arrived any other way was
# unmapped forever. On 2026-08-30 every ad of vl-pulse-nigeria-smoke and
# -smoke-wa was created through the dashboard's Optimize tab, one POST per ad,
# and `ad_attributions` held zero rows in all of production while swoosh
# dropped every respondent those ads recruited.
#
# heal_ad_attributions replaced it rather than joining it: every run compares
# the ads that exist against the rows that exist and fills the gap, so nothing
# depends on having been present when an ad was made. These tests pin the three
# things that must stay true of it -- it adds, it never removes, and it never
# overwrites a row that is already there.


def _healing_study(study_id=STUDY_ID, creative_names=("Creative A", "Creative B")):
    """A study whose conf describes two strata x N creatives on one campaign."""
    creatives = [
        CreativeConf(destination="fly", name=n, template={}) for n in creative_names
    ]

    return StudyConf(
        id=study_id,
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="healing-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[
            FlyMessengerDestination(
                type="messenger",
                name="fly",
                initial_shortcode="mnchweek",
                welcome_message="Welcome!",
                button_text="OK",
            )
        ],
        audiences=[],
        creatives=creatives,
        strata=[
            StratumConf(
                id=sid,
                quota=1.0,
                creatives=list(creative_names),
                facebook_targeting={},
                metadata={"gender": gender},
                question_targeting=None,
                audiences=[],
                excluded_audiences=[],
            )
            for sid, gender in (("stratum-men", "men"), ("stratum-women", "women"))
        ],
        recruitment=SimpleRecruitment(
            ad_campaign_name="healing-campaign",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="CONVERSATIONS",
            min_budget=1,
            budget=100,
            max_sample=100,
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 9, 1),
        ),
    )


class _FakeCampaignState:
    def __init__(self, name, state):
        self.campaign_name = name
        self.campaign_state = state


class _FakeState:
    """The bit of FacebookState healing reads: live adsets and their ads.

    Adsets and ads are plain dicts because that is all `heal_ad_attributions`
    asks of them -- a name and an id. A campaign the study names but Facebook
    does not have raises StateNameError, exactly as CampaignState.campaign does
    for a study that has not published yet.
    """

    def __init__(self, by_campaign):
        self._by_campaign = by_campaign

    def campaign_state(self, name):
        if name not in self._by_campaign:
            raise StateNameError(f"No campaign found with name: {name}")
        return _FakeCampaignState(name, self._by_campaign[name])


def _live(*pairs):
    """[(adset_name, [(ad_id, ad_name), ...]), ...] -> the campaign_state shape."""
    return [
        ({"name": adset_name}, [{"id": i, "name": n} for i, n in ads])
        for adset_name, ads in pairs
    ]


def _one_campaign(*pairs):
    return _FakeState({"healing-campaign": _live(*pairs)})


def _rows_by_ad():
    return {r["ad_id"]: r for r in _all_rows()}


def test_healing_writes_a_row_for_every_live_ad_that_has_none():
    """The whole point: ads created by some other path get mapped anyway."""
    _reset_db()
    study = _healing_study()
    state = _one_campaign(
        ("stratum-men", [("ad-1", "Creative A"), ("ad-2", "Creative B")]),
        ("stratum-women", [("ad-3", "Creative A"), ("ad-4", "Creative B")]),
    )

    healed = heal_ad_attributions(study, state, cnf)

    assert sorted(healed) == ["ad-1", "ad-2", "ad-3", "ad-4"]

    rows = _rows_by_ad()
    assert rows["ad-1"]["stratum_id"] == "stratum-men"
    assert rows["ad-1"]["creative_name"] == "Creative A"
    assert rows["ad-4"]["stratum_id"] == "stratum-women"
    assert rows["ad-4"]["creative_name"] == "Creative B"


def test_healing_matches_an_ad_to_its_stratum_by_adset_name_not_by_order():
    """The join key is (adset name, ad name) -- the same key ad_dif uses.

    Two adsets carry ads with identical names, which is the normal shape: one
    creative per stratum. Getting this wrong attributes every respondent to the
    wrong stratum and nothing downstream can tell, because the row resolves.
    """
    _reset_db()
    study = _healing_study()
    state = _one_campaign(
        ("stratum-women", [("w", "Creative A")]),
        ("stratum-men", [("m", "Creative A")]),
    )

    heal_ad_attributions(study, state, cnf)

    rows = _rows_by_ad()
    assert rows["w"]["stratum_id"] == "stratum-women"
    assert rows["m"]["stratum_id"] == "stratum-men"
    assert rows["w"]["metadata"]["gender"] == "women"
    assert rows["m"]["metadata"]["gender"] == "men"


def test_healing_freezes_the_same_blob_a_create_time_write_would_have():
    """A healed row is not a different kind of row. Same metadata contract.

    `creative` and `form` are the two keys stratum.metadata lacks; a healed row
    missing them would resolve and then match no extraction conf.
    """
    _reset_db()
    study = _healing_study()
    heal_ad_attributions(study, _one_campaign(("stratum-men", [("a", "Creative A")])), cnf)

    md = _rows_by_ad()["a"]["metadata"]
    assert md["creative"] == "Creative A"
    assert md["form"] == "mnchweek"
    assert md["gender"] == "men"


def test_healing_never_overwrites_an_existing_row():
    """Invariant 3. A snapshot beats a reconstruction, always.

    The conf has moved on since the ad was built -- different stratum, different
    metadata. Healing must leave the frozen row exactly as it was rather than
    "correcting" it to today's answer.
    """
    _reset_db()
    study = _healing_study()

    frozen = _provenance(
        stratum_id="stratum-as-it-was",
        creative_name="Creative A",
        metadata={"creative": "Creative A", "form": "old-form", "gender": "nonbinary"},
    )
    create_ad_attribution("ad-1", frozen, cnf)

    healed = heal_ad_attributions(
        study, _one_campaign(("stratum-men", [("ad-1", "Creative A")])), cnf
    )

    assert healed == []
    row = _rows_by_ad()["ad-1"]
    assert row["stratum_id"] == "stratum-as-it-was"
    assert row["metadata"]["gender"] == "nonbinary"


def test_healing_is_idempotent():
    """Every run heals. Running it twice must cost nothing and change nothing."""
    _reset_db()
    study = _healing_study()
    state = _one_campaign(("stratum-men", [("ad-1", "Creative A")]))

    assert heal_ad_attributions(study, state, cnf) == ["ad-1"]
    assert heal_ad_attributions(study, state, cnf) == []
    assert len(_all_rows()) == 1


def test_healing_never_removes_a_row_whose_ad_is_gone():
    """Invariant 2, and the reason healing is add-only.

    Respondents keep arriving from ads that no longer exist -- a page post can
    be reshared indefinitely -- so an ad's absence from Facebook is never
    evidence that its row should go.
    """
    _reset_db()
    study = _healing_study()
    create_ad_attribution("deleted-ad", _provenance(stratum_id="stratum-men"), cnf)

    heal_ad_attributions(study, _one_campaign(("stratum-men", [])), cnf)

    assert _rows_by_ad()["deleted-ad"]["stratum_id"] == "stratum-men"


def test_healing_touches_no_other_study():
    _reset_db()
    create_ad_attribution("theirs", _provenance(study_id=OTHER_STUDY_ID), cnf)

    heal_ad_attributions(
        _healing_study(), _one_campaign(("stratum-men", [("mine", "Creative A")])), cnf
    )

    rows = _rows_by_ad()
    assert str(rows["theirs"]["study_id"]) == OTHER_STUDY_ID
    assert str(rows["mine"]["study_id"]) == STUDY_ID


def test_healing_skips_an_ad_the_conf_no_longer_describes():
    """The one hole healing cannot fill, and it must not guess.

    An ad whose (adset, creative) pair is not in the conf has nothing left to
    say what it meant. Inventing a row would attribute its respondents to a
    stratum they were never recruited into, which is worse than counting none.
    """
    _reset_db()
    study = _healing_study()
    state = _one_campaign(
        ("stratum-men", [("known", "Creative A"), ("orphan", "Creative Deleted")]),
        ("stratum-that-was-renamed", [("stale", "Creative A")]),
    )

    healed = heal_ad_attributions(study, state, cnf)

    assert healed == ["known"]
    assert set(_rows_by_ad()) == {"known"}


def test_healing_is_quiet_for_a_study_whose_campaign_does_not_exist_yet():
    """Every study looks like this before its first run. Not a failure."""
    _reset_db()

    assert heal_ad_attributions(_healing_study(), _FakeState({}), cnf) == []
    assert _all_rows() == []


def test_healing_needs_no_graph_lookup_for_audiences():
    """The repair path must not share failure modes with the thing it repairs.

    Strata are hydrated with resolve_audiences=False, so a study whose stratum
    names a custom audience can still be healed with `state` that would raise
    on any audience lookup. Passing a state that has no audience machinery at
    all is the assertion.
    """
    _reset_db()
    study = _healing_study()
    study.strata[0].excluded_audiences = ["an-audience-that-is-not-on-facebook"]

    healed = heal_ad_attributions(
        study, _one_campaign(("stratum-men", [("ad-1", "Creative A")])), cnf
    )

    assert healed == ["ad-1"]
