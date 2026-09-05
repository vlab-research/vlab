"""Tests for `sdk/study.py` -- the file, the diff, the push order.

No database and no HTTP: this module is pure, and that is most of why it is a
module rather than code inside the CLI.

The diff tests are the ones that matter. A diff that reports a spurious change
is not a cosmetic bug here: `vlab push` writes what the diff says differs, and
`study_confs` is append-only, so a permanently-wrong diff appends a row on
every push forever and there is no way to remove any of them.
"""

import json

import pytest
import yaml

from ..authoring.validate import validate_study
from .study import (
    PUSH_ORDER,
    SECTION_URL_SEGMENTS,
    SECTIONS,
    StudyFile,
    diff_sections,
    infer_recruitment_type,
    model_dump_section,
    normalise_section,
    push_plan,
    skeleton,
    unknown_keys,
    value_diff,
)

ORG = "9d3d0f6a-0f0f-4b2a-9b7e-000000000001"

SIMPLE_RECRUITMENT = {
    "ad_campaign_name": "hpv",
    "objective": "OUTCOME_ENGAGEMENT",
    "optimization_goal": "LINK_CLICKS",
    "min_budget": 100,
    "budget": 10000,
    "max_sample": 1000,
    "start_date": "2026-01-01T00:00:00",
    "end_date": "2026-03-01T00:00:00",
}

MESSENGER = {
    "type": "messenger",
    "name": "main",
    "initial_shortcode": "abc123",
    "welcome_message": "hello",
    "button_text": "Start",
}


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------


def test_a_file_is_a_header_plus_the_nine_sections():
    text = yaml.safe_dump(
        {
            "org": ORG,
            "slug": "hpv",
            "name": "HPV",
            "recruitment": SIMPLE_RECRUITMENT,
            "destinations": [MESSENGER],
        }
    )

    study = StudyFile.loads(text)

    assert study.org == ORG
    assert study.slug == "hpv"
    assert study.name == "HPV"
    assert set(study.sections) == {"recruitment", "destinations"}


def test_json_loads_too():
    """YAML 1.1 parses JSON, so one loader covers both formats."""
    study = StudyFile.loads(json.dumps({"org": ORG, "slug": "s", "strata": []}))
    assert study.sections == {"strata": []}


def test_an_empty_file_is_an_empty_study_not_a_crash():
    assert StudyFile.loads("").sections == {}


def test_a_file_that_is_not_a_mapping_says_so():
    with pytest.raises(ValueError) as e:
        StudyFile.loads("- one\n- two\n")
    assert "mapping" in str(e.value)


def test_an_unrecognised_top_level_key_is_kept_not_dropped():
    """A typo'd section name would otherwise vanish on the next save, taking
    whatever the author wrote in it."""
    study = StudyFile.loads(yaml.safe_dump({"org": ORG, "stratas": [1]}))
    assert study.extra == {"stratas": [1]}
    assert "stratas" in study.dumps()


def test_saving_orders_header_then_sections_canonically(tmp_path):
    study = StudyFile(
        org=ORG,
        slug="hpv",
        sections={"strata": [], "general": {"name": "x"}},
    )
    path = study.save(str(tmp_path / "study.yaml"))

    text = open(path).read()
    assert text.index("org:") < text.index("general:") < text.index("strata:")


def test_a_json_extension_writes_json(tmp_path):
    study = StudyFile(org=ORG, slug="hpv", sections={"strata": []})
    path = study.save(str(tmp_path / "study.json"))
    assert json.loads(open(path).read())["slug"] == "hpv"


def test_round_trip_preserves_everything(tmp_path):
    original = StudyFile(
        org=ORG,
        slug="hpv",
        name="HPV",
        sections={"recruitment": SIMPLE_RECRUITMENT, "destinations": [MESSENGER]},
        extra={"notes": "mine"},
    )
    path = original.save(str(tmp_path / "s.yaml"))

    assert StudyFile.load(path).to_dict() == original.to_dict()


def test_require_target_names_what_is_missing():
    with pytest.raises(ValueError) as e:
        StudyFile(slug="hpv").require_target()
    assert "org" in str(e.value)


def test_from_confs_keeps_a_conf_type_outside_the_nine():
    """`study_confs.conf_type` has no constraint, so a row written by something
    other than the nine routes is possible. Losing it on a pull would be worse
    than carrying it."""
    study = StudyFile.from_confs(ORG, "hpv", {"strata": [], "mystery": {"a": 1}})
    assert study.sections == {"strata": []}
    assert study.extra == {"mystery": {"a": 1}}


# ---------------------------------------------------------------------------
# The skeleton
# ---------------------------------------------------------------------------


def test_the_skeleton_parses_as_a_study_file():
    study = StudyFile.loads(skeleton(org=ORG, slug="hpv", name="HPV"))
    assert study.org == ORG
    assert set(study.sections) == set(SECTIONS)


def test_the_skeleton_is_a_valid_study():
    """Not merely syntactically valid. A skeleton that fails `vlab validate`
    the moment it is written would teach every new user to ignore the
    validator."""
    study = StudyFile.loads(skeleton(org=ORG, slug="hpv", name="HPV"))
    report = validate_study(study.sections)
    assert report.valid, [e.model_dump() for e in report.errors]


def test_the_skeleton_writes_the_recruitment_tag():
    """New configuration should be explicit about which arm of the union it is,
    whether or not the server it is written against reads the tag yet."""
    study = StudyFile.loads(skeleton())
    assert study.sections["recruitment"]["type"] == "simple"


# ---------------------------------------------------------------------------
# The union tags
# ---------------------------------------------------------------------------


def test_the_recruitment_tag_is_inferred_from_shape():
    assert infer_recruitment_type({"ad_campaign_name": "x"}) == "simple"
    assert infer_recruitment_type({"ad_campaign_name_base": "x", "arms": 3}) == (
        "pipeline_experiment"
    )
    assert infer_recruitment_type(
        {"ad_campaign_name_base": "x", "destinations": []}
    ) == ("destination")


def test_arms_beats_destinations_because_the_untagged_union_does_too():
    """The order is load-bearing. An over-specified body resolves to the
    pipeline arm under pydantic's untagged union today, and a diff that decided
    otherwise would claim a study's recruitment strategy had changed."""
    assert infer_recruitment_type({"arms": 2, "destinations": ["a"]}) == (
        "pipeline_experiment"
    )


def test_nothing_to_go_on_infers_nothing():
    assert infer_recruitment_type({}) is None
    assert infer_recruitment_type({"budget": 1}) is None


def test_an_explicit_tag_is_returned_unchanged():
    assert infer_recruitment_type({"type": "destination", "arms": 2}) == "destination"


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def test_normalisation_fills_the_defaults_the_server_would_fill():
    """The server stores `model_dump()`, not your body. Without reproducing
    that, a file omitting `extra_metadata` would diff against itself forever."""
    sent = {
        "name": "x",
        "credentials_key": "Facebook",
        "credentials_entity": "facebook",
        "ad_account": "123",
        "opt_window": 48,
    }
    assert normalise_section("general", sent)["extra_metadata"] == {}


def test_normalisation_renders_dates_as_the_stored_json_does():
    """`mode="json"`, not `mode="python"`: the stored value went through
    orjson, so it is an ISO string. A datetime object here would make every
    recruitment conf differ from itself."""
    dumped = model_dump_section("recruitment", SIMPLE_RECRUITMENT)
    assert dumped["start_date"] == "2026-01-01T00:00:00"


def test_a_section_that_does_not_parse_falls_back_to_raw():
    assert model_dump_section("general", {"nonsense": 1}) is None
    assert normalise_section("general", {"nonsense": 1}) == {"nonsense": 1}


def test_an_audience_with_no_subtype_does_not_crash_normalisation():
    """`AudienceConf`'s before-validator raises a bare KeyError rather than a
    pydantic error for this (plan §14.4), so catching ValidationError alone
    would not have been enough."""
    assert model_dump_section("audiences", [{"name": "a"}]) is None


# ---------------------------------------------------------------------------
# The diff
# ---------------------------------------------------------------------------


def _diff(local, stored):
    return {d.section: d for d in diff_sections(local, stored)}


def test_identical_sections_are_unchanged():
    local = {"destinations": [MESSENGER]}
    stored = {"destinations": [MESSENGER]}
    assert _diff(local, stored)["destinations"].status == "unchanged"


def test_a_section_only_in_the_file_is_new():
    assert _diff({"destinations": [MESSENGER]}, {})["destinations"].status == "new"


def test_a_section_only_on_the_server_is_remote_only():
    """Never "deleted": there is no way to remove a section through the API at
    all, so push leaves it alone."""
    d = _diff({}, {"destinations": [MESSENGER]})["destinations"]
    assert d.status == "remote_only"
    assert not d.needs_push


def test_a_changed_value_is_changed():
    stored = {"destinations": [MESSENGER]}
    local = {"destinations": [{**MESSENGER, "welcome_message": "hi"}]}
    assert _diff(local, stored)["destinations"].status == "changed"


def test_a_file_omitting_a_defaulted_field_is_not_a_change():
    """The single commonest false positive, and the reason normalisation goes
    through the model at all."""
    sent = {
        "name": "x",
        "credentials_key": "Facebook",
        "credentials_entity": "facebook",
        "ad_account": "123",
        "opt_window": 48,
    }
    stored = {**sent, "extra_metadata": {}}
    assert _diff({"general": sent}, {"general": stored})["general"].status == (
        "unchanged"
    )


# -- the type tag, in both directions ---------------------------------------


def test_a_type_tag_the_server_added_is_not_a_change():
    """A server on PR #262 or later stores a `type` on every recruitment conf,
    because `model_dump()` emits one. A file written before that carries none."""
    stored = {**SIMPLE_RECRUITMENT, "type": "simple"}
    assert (
        _diff({"recruitment": SIMPLE_RECRUITMENT}, {"recruitment": stored})[
            "recruitment"
        ].status
        == "unchanged"
    )


def test_a_type_tag_the_file_writes_is_not_a_change_against_an_older_server():
    """The other direction, which is the one that would bite hardest: a server
    older than #262 drops the tag on the way in, so a file that writes it (and
    it should) would otherwise re-push recruitment on every single run."""
    local = {**SIMPLE_RECRUITMENT, "type": "simple"}
    assert (
        _diff({"recruitment": local}, {"recruitment": SIMPLE_RECRUITMENT})[
            "recruitment"
        ].status
        == "unchanged"
    )


def test_a_type_tag_that_disagrees_with_the_shape_is_surfaced():
    """Tolerance covers a tag that restates the body, and only that.

    A tag that CONTRADICTS the body is reported -- but as an unknown key rather
    than as a change, and the distinction is version skew again. Against a
    server older than PR #262 the tag is an undeclared field: the server drops
    it exactly as normalisation does, so pushing really would store what is
    stored, and calling that a change would be false. What is true either way
    is that `type: destination` on a body with `ad_campaign_name` is wrong, and
    that is what the `!` line says.

    On a server from #262 onwards the same body is a 422 from the discriminated
    union, and it is `push` that reports it.
    """
    local = {**SIMPLE_RECRUITMENT, "type": "destination"}
    d = _diff({"recruitment": local}, {"recruitment": SIMPLE_RECRUITMENT})[
        "recruitment"
    ]
    assert d.unknown == ("type",)


def test_the_messenger_default_on_a_destination_is_not_a_change():
    """An absent destination `type` is defaulted to messenger for the 45 stored
    confs that predate the field."""
    without = {k: v for k, v in MESSENGER.items() if k != "type"}
    assert (
        _diff({"destinations": [without]}, {"destinations": [MESSENGER]})[
            "destinations"
        ].status
        == "unchanged"
    )


def test_a_different_destination_type_is_still_a_change():
    web = {"type": "web", "name": "main", "url_template": "https://x/{ref}"}
    assert (
        _diff({"destinations": [web]}, {"destinations": [MESSENGER]})[
            "destinations"
        ].status
        == "changed"
    )


# ---------------------------------------------------------------------------
# Unknown keys
# ---------------------------------------------------------------------------


def test_a_misspelled_top_level_field_is_reported():
    d = _diff({"destinations": [{**MESSENGER, "welcom_message": "hi"}]}, {})
    assert d["destinations"].unknown == ("[0].welcom_message",)


def test_a_misspelled_nested_field_is_reported():
    """Depth is the point: a typo at `levels[].facebok_targeting` is exactly as
    silent as one at the top level."""
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "t",
                    "template_adset": "t",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                    "quotaa": 0.5,
                }
            ],
        }
    ]
    assert unknown_keys("variables", variables) == ["[0].levels[0].quotaa"]


def test_arbitrary_key_fields_are_not_unknown_keys():
    """`facebook_targeting`, `template` and `metadata` hold whatever their
    owner puts in them. An unknown key there is the feature."""
    stratum = {
        "id": "a",
        "quota": 1.0,
        "creatives": [],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {"anything_at_all": 1},
        "question_targeting": None,
        "metadata": {"whatever": "yes"},
    }
    assert unknown_keys("strata", [stratum]) == []


def test_the_recruitment_type_tag_is_not_reported_as_unknown():
    """On a server older than #262 it genuinely is an undeclared key, and
    reporting it would tell every user of our own skeleton that their file is
    wrong."""
    assert unknown_keys("recruitment", {**SIMPLE_RECRUITMENT, "type": "simple"}) == []


def test_a_section_that_does_not_parse_reports_no_unknown_keys():
    """Whatever is wrong with it is not "an extra key", and `validate` will
    have said so with a better message."""
    assert unknown_keys("general", {"nonsense": 1}) == []


# ---------------------------------------------------------------------------
# value_diff
# ---------------------------------------------------------------------------


def test_value_diff_reaches_the_leaf():
    changes = value_diff({"a": {"b": 1}}, {"a": {"b": 2}})
    assert changes == [("a.b", 1, 2)]


def test_value_diff_indexes_lists():
    changes = value_diff([{"q": 1}, {"q": 2}], [{"q": 1}, {"q": 3}])
    assert changes == [("[1].q", 2, 3)]


def test_value_diff_distinguishes_absent_from_null():
    """`creatives[].tags` is genuinely null; that is not the same as absent."""
    ((path, stored, local),) = value_diff({"a": None}, {})
    assert path == "a"
    assert stored is None
    assert repr(local) == "(absent)"


# ---------------------------------------------------------------------------
# Push ordering
# ---------------------------------------------------------------------------


def test_push_order_writes_references_before_the_things_that_name_them():
    assert PUSH_ORDER.index("destinations") < PUSH_ORDER.index("creatives")
    assert PUSH_ORDER.index("creatives") < PUSH_ORDER.index("strata")
    assert PUSH_ORDER.index("data_sources") < PUSH_ORDER.index("inference_data")


def test_recruitment_is_written_last():
    """Its start/end window is what makes the study visible to the crons, so
    writing it last means the two-hourly run cannot pick up a half-configured
    study."""
    assert PUSH_ORDER[-1] == "recruitment"


def test_push_order_covers_exactly_the_nine():
    assert set(PUSH_ORDER) == set(SECTIONS)
    assert len(PUSH_ORDER) == len(SECTIONS)


def test_push_plan_orders_and_skips_unchanged():
    local = {
        "strata": [],
        "destinations": [MESSENGER],
        "recruitment": SIMPLE_RECRUITMENT,
    }
    stored = {"destinations": [MESSENGER]}
    plan = push_plan(diff_sections(local, stored))
    assert [d.section for d in plan] == ["strata", "recruitment"]


def test_the_two_hyphenated_url_segments():
    """You POST to `confs/data-sources` and the row is stored as
    `data_sources`. Two of the nine differ, and it is a real trap."""
    assert SECTION_URL_SEGMENTS["data_sources"] == "data-sources"
    assert SECTION_URL_SEGMENTS["inference_data"] == "inference-data"
    assert SECTION_URL_SEGMENTS["strata"] == "strata"
