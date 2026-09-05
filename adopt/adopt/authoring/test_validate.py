"""Tests for whole-study validation.

Organised as one complete, valid study (`valid_study()`) plus one deliberate
break per finding class. The valid study is the important half: a validator
that reports nothing on a working study is the only thing that makes a report
worth reading, and every "break" test starts from it so a false positive shows
up as the valid case going red rather than as a silently over-strict rule.
"""

from copy import deepcopy

import pytest

from ..malaria import warn_on_incomplete_targeting, warn_on_thinned_ref_without_mapping
from ..study_conf import (
    StudyConf,
    missing_targeting_variables,
    thins_its_ref_without_reading_the_mapping,
)
from .validate import (
    REQUIRED_SECTIONS,
    SECTIONS,
    audience_names_created_by,
    study_conf_from_sections,
    validate_study,
)
from ..study_conf import AudienceConf, Lookalike, LookalikeSpec, Partitioning


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def valid_study() -> dict:
    """A complete study, in the wire shape `get_all_study_confs` returns.

    Deliberately exercises every edge of the reference graph
    (`documentation/agent-api.md` §1.3) at least once: two strata naming two
    creatives, creatives naming two destinations, a stratum naming one audience
    and excluding another, question_targeting on a variable an extraction conf
    supplies, and an inference_data key naming a real data source.
    """
    return {
        "general": {
            "name": "test-study",
            "credentials_key": "Facebook",
            "credentials_entity": "facebook",
            "ad_account": "1234567890",
            "opt_window": 48,
            "extra_metadata": {},
        },
        "recruitment": {
            "ad_campaign_name": "test-campaign",
            "objective": "OUTCOME_ENGAGEMENT",
            "optimization_goal": "LINK_CLICKS",
            "destination_type": "MESSENGER",
            "min_budget": 100,
            "budget": 10000,
            "max_sample": 1000,
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-03-01T00:00:00",
        },
        "destinations": [
            {
                "type": "messenger",
                "name": "main",
                "initial_shortcode": "abc123",
                "welcome_message": "hello",
                "button_text": "Start",
            },
            {
                "type": "web",
                "name": "site",
                "url_template": "https://example.com/?ref={ref}",
            },
        ],
        "creatives": [
            {"name": "smiling", "destination": "main", "template": {"actor_id": "1"}},
            {"name": "frowning", "destination": "site", "template": {"actor_id": "1"}},
        ],
        # Both CUSTOM, because a PARTITIONED or LOOKALIKE audience cannot be
        # expressed as wire JSON at all — see
        # test_a_partitioned_audience_cannot_be_written_as_json.
        "audiences": [
            {"name": "respondents", "subtype": "CUSTOM"},
            {"name": "already-asked", "subtype": "CUSTOM"},
        ],
        "variables": [
            {
                "name": "gender",
                "properties": ["genders"],
                "levels": [
                    {
                        "name": "men",
                        "template_campaign": "tc",
                        "template_adset": "ta",
                        "facebook_targeting": {"genders": [1]},
                        "quota": 0.5,
                    }
                ],
            }
        ],
        "strata": [
            {
                "id": "men",
                "quota": 0.5,
                "creatives": ["smiling"],
                "audiences": ["respondents"],
                "excluded_audiences": ["already-asked"],
                "facebook_targeting": {"genders": [1]},
                "question_targeting": {
                    "op": "equal",
                    "vars": [
                        {"type": "variable", "value": "gender"},
                        {"type": "constant", "value": "man"},
                    ],
                },
                "metadata": {"stratum_gender": "men"},
            },
            {
                "id": "women",
                "quota": 0.5,
                "creatives": ["frowning"],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {"genders": [2]},
                "question_targeting": None,
                "metadata": {"stratum_gender": "women"},
            },
        ],
        "data_sources": [
            {"name": "fly", "source": "fly", "credentials_key": "fly", "config": None}
        ],
        "inference_data": {
            "data_sources": {
                "fly": {
                    "user_variable": "userid",
                    "extraction_confs": [
                        {
                            "location": "metadata",
                            "key": "stratum_gender",
                            "name": "gender",
                            "functions": [],
                            "value_type": "categorical",
                            "aggregate": "last",
                        }
                    ],
                }
            }
        },
    }


def broken(**overrides) -> dict:
    """The valid study with sections replaced. `None` removes the section."""
    study = deepcopy(valid_study())
    for key, value in overrides.items():
        if value is None:
            study.pop(key, None)
        else:
            study[key] = value
    return study


def codes(messages):
    return [m.code for m in messages]


# ---------------------------------------------------------------------------
# The valid case
# ---------------------------------------------------------------------------


def test_a_complete_study_is_valid_with_no_findings_at_all():
    report = validate_study(valid_study())

    # Both lists, not just `valid`: a warning on a correct study is noise, and
    # noise is what stops anyone reading the report.
    assert report.errors == []
    assert report.warnings == []
    assert report.valid is True


def test_the_fixture_actually_assembles_a_studyconf():
    # Guards the fixture itself. If this study could not be assembled the
    # "valid" test above would be asserting that the validator misses things.
    study = study_conf_from_sections(valid_study())
    assert isinstance(study, StudyConf)
    assert [s.id for s in study.strata] == ["men", "women"]


def test_every_section_the_endpoint_accepts_is_in_the_fixture():
    assert set(valid_study()) == set(SECTIONS)


# ---------------------------------------------------------------------------
# Missing sections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_a_missing_required_section_is_an_error(section):
    report = validate_study(broken(**{section: None}))

    missing = [e for e in report.errors if e.code == "section.missing"]
    assert [e.section for e in missing] == [section]
    assert report.valid is False


def test_an_explicit_none_means_the_same_as_absent():
    study = valid_study()
    study["general"] = None

    report = validate_study(study)
    assert [(e.code, e.section) for e in report.errors] == [
        ("section.missing", "general")
    ]


def test_the_optional_sections_may_be_missing():
    # inference_data and data_sources are Optional on StudyConf, and a study
    # that has not been wired to a survey platform yet is not broken. It does
    # earn the targeting warning, which is the point of that warning.
    report = validate_study(broken(inference_data=None, data_sources=None))

    assert codes(report.errors) == []
    assert report.valid is True
    assert "stratum.targeting_variable_unsupplied" in codes(report.warnings)


def test_variables_may_be_missing_because_it_is_inert():
    report = validate_study(broken(variables=None))
    assert report.valid is True
    assert report.warnings == []


def test_an_empty_study_reports_every_required_section_at_once():
    report = validate_study({})

    # Every one, in one pass — not the first and a promise to tell you the rest
    # after you fix it.
    assert set(e.section for e in report.errors) == set(REQUIRED_SECTIONS)
    assert all(e.code == "section.missing" for e in report.errors)


def test_an_unrecognised_section_is_a_warning_not_an_error():
    report = validate_study(broken(strataa=[]))

    assert report.valid is True
    assert codes(report.warnings) == ["section.unrecognized"]
    assert report.warnings[0].path == "strataa"


# ---------------------------------------------------------------------------
# Per-section (pydantic) errors
# ---------------------------------------------------------------------------


def test_a_section_that_does_not_parse_reports_every_field_at_once():
    report = validate_study(broken(strata=[{"id": "men"}]))

    assert report.valid is False
    invalid = [e for e in report.errors if e.code == "section.invalid"]
    # quota, creatives, audiences, excluded_audiences, facebook_targeting,
    # metadata — six missing fields, six findings.
    assert len(invalid) == 6
    assert all(e.section == "strata" for e in invalid)
    assert "strata[0].quota" in [e.path for e in invalid]


def test_two_broken_sections_are_both_reported():
    report = validate_study(
        broken(strata=[{"id": "men"}], general={"name": "only-a-name"})
    )

    sections = {e.section for e in report.errors if e.code == "section.invalid"}
    assert sections == {"strata", "general"}


def test_a_broken_section_is_not_also_reported_as_missing():
    report = validate_study(broken(general={"name": "only-a-name"}))

    assert "section.missing" not in codes(report.errors)


def test_a_section_of_the_wrong_json_type_is_an_error_not_a_crash():
    report = validate_study(broken(strata={"not": "a list"}))

    assert report.valid is False
    assert codes(report.errors) == ["section.invalid"]


def test_an_audience_with_no_subtype_is_an_error_not_a_keyerror():
    # AudienceConf's mode="before" validator does values["subtype"], and
    # pydantic wraps only ValueError and AssertionError — so this raises a bare
    # KeyError out of validate_python. Before the guard in _parse_sections it
    # crashed the validator, which through the endpoint would have been a 500
    # for a report whose whole job is describing bad input.
    report = validate_study(broken(audiences=[{"name": "respondents"}]))

    assert report.valid is False
    invalid = [e for e in report.errors if e.code == "section.invalid"]
    assert [e.section for e in invalid] == ["audiences"]
    assert "KeyError" in invalid[0].message


def test_cross_section_checks_still_run_when_another_section_is_broken():
    # The point of parsing sections independently. A broken recruitment conf
    # must not hide a dangling creative reference.
    study = broken(recruitment={"nonsense": True})
    study["strata"][0]["creatives"] = ["does-not-exist"]

    report = validate_study(study)

    assert "section.invalid" in codes(report.errors)
    assert "stratum.creative_unknown" in codes(report.errors)


# ---------------------------------------------------------------------------
# Whole-study (StudyConf) validators
# ---------------------------------------------------------------------------


def test_a_whatsapp_ref_that_fly_cannot_parse_is_a_study_error():
    # check_whatsapp_refs_are_deliverable: a metadata-mode WhatsApp destination
    # carrying a stratum value with a "/" in it. Today this raises hours later,
    # at StudyConf assembly inside a cron.
    #
    # "/" rather than a space, deliberately: metadata values are percent-encoded
    # now, so almost everything survives the entry pattern and "/" is what
    # `quote()` leaves literal (`whatsapp_ref_token_safe`, study_conf.py:258).
    study = broken(
        destinations=[
            {
                "type": "whatsapp",
                "name": "main",
                "initial_shortcode": "abc123",
                "welcome_message": "hello",
                "whatsapp_phone_number": "+1-541-920-2635",
            },
            {
                "type": "web",
                "name": "site",
                "url_template": "https://example.com/?ref={ref}",
            },
        ]
    )
    study["strata"][0]["metadata"] = {"stratum_gender": "men/women"}

    report = validate_study(study)

    assert report.valid is False
    assert "study.invalid" in codes(report.errors)
    assert "fly's WhatsApp entry pattern cannot parse" in "".join(
        e.message for e in report.errors
    )


def test_whole_study_validators_do_not_run_when_a_section_is_broken():
    # Running them would mean re-parsing the raw sections and reporting every
    # field error a second time under a different code.
    report = validate_study(broken(general={"name": "only-a-name"}))
    assert "study.invalid" not in codes(report.errors)


# ---------------------------------------------------------------------------
# Dangling references
# ---------------------------------------------------------------------------


def test_a_stratum_naming_an_unknown_creative_is_an_error():
    study = valid_study()
    study["strata"][0]["creatives"] = ["smiling", "nope"]

    report = validate_study(study)

    assert report.valid is False
    finding = next(e for e in report.errors if e.code == "stratum.creative_unknown")
    assert finding.path == "strata[0].creatives[1]"
    assert "'nope'" in finding.message
    # The message names the stratum, which the run-time KeyError does not.
    assert "'men'" in finding.message


def test_a_creative_naming_an_unknown_destination_is_an_error():
    study = valid_study()
    study["creatives"][1]["destination"] = "nope"

    report = validate_study(study)

    assert report.valid is False
    finding = next(e for e in report.errors if e.code == "creative.destination_unknown")
    assert finding.path == "creatives[1].destination"


def test_a_stratum_naming_an_unknown_audience_is_a_warning():
    # Warning, not error: the name resolves against the ad account's custom
    # audiences, which may hold one built by hand in Ads Manager.
    study = valid_study()
    study["strata"][0]["audiences"] = ["built-in-ads-manager"]

    report = validate_study(study)

    assert report.valid is True
    finding = next(w for w in report.warnings if w.code == "stratum.audience_unknown")
    assert finding.path == "strata[0].audiences[0]"


def test_a_dangling_exclusion_gets_its_own_code_and_says_what_it_costs():
    study = valid_study()
    study["strata"][0]["excluded_audiences"] = ["nope"]

    report = validate_study(study)

    finding = next(
        w for w in report.warnings if w.code == "stratum.excluded_audience_unknown"
    )
    assert "re-recruit people it meant to exclude" in finding.message


def test_a_partitioned_audience_cannot_be_written_as_json():
    """A defect this work found, recorded rather than fixed.

    `AudienceConf`'s `mode="before"` validator asserts
    `isinstance(values["partitioning"], Partitioning)` — an isinstance check
    against the *parsed* model, run BEFORE pydantic has parsed anything. So a
    partitioned (or lookalike) audience is only constructible from Python
    objects, never from the JSON the API speaks, and `POST /confs/audiences`
    with one is a 422. Every existing test in this repo builds them from
    objects (`test_audiences.py:217`, `test_marketing.py:306`), which is why
    nobody has hit it.

    The validator's job here is to say so rather than to hide it: a study with
    a stored partitioned audience conf fails `StudyConf` assembly in the cron
    for exactly this reason, so `section.invalid` is the true answer.

    Fixing it belongs in its own change — see
    planning/agent-study-authoring.md §14.
    """
    report = validate_study(
        broken(
            audiences=[
                {"name": "respondents", "subtype": "CUSTOM"},
                {
                    "name": "cohorts",
                    "subtype": "PARTITIONED",
                    "partitioning": {"min_users": 100},
                },
            ]
        )
    )

    assert report.valid is False
    invalid = [e for e in report.errors if e.code == "section.invalid"]
    assert [e.path for e in invalid] == ["audiences[1]"]
    assert "requires a" in invalid[0].message


def _audiences_with_a_partitioned_one():
    """The audiences section as *models*, which is the only way to build one.

    `validate_study` accepts already-parsed models alongside wire values (they
    pass straight through the TypeAdapter), which is how the SDK will hand it a
    study it built in Python. Used here so the partitioned naming rule can be
    tested at all until the defect above is fixed.
    """
    return [
        AudienceConf(name="respondents", subtype="CUSTOM"),
        AudienceConf(
            name="cohorts", subtype="PARTITIONED", partitioning=Partitioning(min_users=100)
        ),
    ]


def test_naming_a_partitioned_audience_by_its_conf_name_is_an_error():
    # The case §11.4 item 4 singles out: vlab creates `cohorts-cohort-N` and
    # never `cohorts`, so this reference can never resolve.
    study = broken(audiences=_audiences_with_a_partitioned_one())
    study["strata"][0]["audiences"] = ["cohorts"]

    report = validate_study(study)

    assert report.valid is False
    finding = next(
        e for e in report.errors if e.code == "audience.partitioned_bare_name"
    )
    assert finding.path == "strata[0].audiences[0]"
    assert "cohorts-cohort-1" in finding.message


def test_excluding_a_partitioned_audience_by_its_conf_name_is_also_an_error():
    study = broken(audiences=_audiences_with_a_partitioned_one())
    study["strata"][0]["excluded_audiences"] = ["cohorts"]

    report = validate_study(study)

    finding = next(
        e for e in report.errors if e.code == "audience.partitioned_bare_name"
    )
    assert finding.path == "strata[0].excluded_audiences[0]"
    assert "without the exclusion" in finding.message


def test_a_partitioned_cohort_reference_is_accepted():
    study = broken(audiences=_audiences_with_a_partitioned_one())
    study["strata"][0]["audiences"] = ["cohorts-cohort-3"]
    study["strata"][0]["excluded_audiences"] = []

    report = validate_study(study)
    assert report.warnings == []
    assert report.valid is True


def test_a_cohort_of_an_audience_that_is_not_partitioned_is_still_unknown():
    study = valid_study()
    study["strata"][0]["audiences"] = ["respondents-cohort-1"]

    assert codes(validate_study(study).warnings) == ["stratum.audience_unknown"]


def test_audience_names_created_by_matches_hydrate_audience():
    # Pinned against audiences.py, which is the only thing that names them.
    custom = AudienceConf(name="a", subtype="CUSTOM")
    lookalike = AudienceConf(
        name="a",
        subtype="LOOKALIKE",
        lookalike=Lookalike(
            target=100,
            spec=LookalikeSpec(country="IN", ratio=0.1, starting_ratio=0.0),
        ),
    )
    partitioned = AudienceConf(
        name="a", subtype="PARTITIONED", partitioning=Partitioning(min_users=10)
    )

    assert audience_names_created_by(custom) == ["a"]
    assert audience_names_created_by(lookalike) == ["a-origin", "a"]
    assert audience_names_created_by(partitioned) == []


def test_a_lookalike_audience_may_be_named_directly_or_by_its_origin():
    study = valid_study()
    study["audiences"] = [
        AudienceConf(name="respondents", subtype="CUSTOM"),
        AudienceConf(name="already-asked", subtype="CUSTOM"),
        AudienceConf(
            name="similar",
            subtype="LOOKALIKE",
            lookalike=Lookalike(
                target=100,
                spec=LookalikeSpec(country="IN", ratio=0.1, starting_ratio=0.0),
            ),
        ),
    ]
    study["strata"][0]["audiences"] = ["similar", "similar-origin"]

    assert validate_study(study).warnings == []


def test_duplicate_stratum_ids_are_an_error():
    study = valid_study()
    study["strata"][1]["id"] = "men"

    report = validate_study(study)

    assert report.valid is False
    finding = next(e for e in report.errors if e.code == "stratum.id_duplicated")
    assert finding.path == "strata[1].id"


def test_an_inference_data_key_naming_no_data_source_is_a_warning():
    study = valid_study()
    study["inference_data"]["data_sources"]["typeform"] = study["inference_data"][
        "data_sources"
    ]["fly"]

    report = validate_study(study)

    assert report.valid is True
    finding = next(
        w for w in report.warnings if w.code == "inference_data.source_unknown"
    )
    assert finding.path == "inference_data.data_sources.typeform"


# ---------------------------------------------------------------------------
# The two invariants that used to reach only a log
# ---------------------------------------------------------------------------


def test_targeting_a_variable_nothing_supplies_is_a_warning():
    # documentation/agent-api.md §6 step 8, which until now said "check,
    # yourself ... Nothing else will".
    study = valid_study()
    study["strata"][0]["question_targeting"]["vars"][0]["value"] = "age"

    report = validate_study(study)

    assert report.valid is True
    finding = next(
        w for w in report.warnings if w.code == "stratum.targeting_variable_unsupplied"
    )
    assert finding.path == "strata[0].question_targeting"
    assert "'age'" in finding.message


def test_the_targeting_check_agrees_with_missing_targeting_variables():
    # The validator decomposes missing_targeting_variables into its two pure
    # halves so it can run on a partially-broken study. This pins the
    # decomposition against the original on a study that assembles.
    study = valid_study()
    study["strata"][0]["question_targeting"]["vars"][0]["value"] = "age"

    conf = study_conf_from_sections(study)
    assert set(missing_targeting_variables(conf)) == {"men"}

    report = validate_study(study)
    reported = {
        w.path
        for w in report.warnings
        if w.code == "stratum.targeting_variable_unsupplied"
    }
    assert reported == {"strata[0].question_targeting"}


def test_a_thinned_ref_with_nothing_reading_the_mapping_is_a_warning():
    study = valid_study()
    study["destinations"][0]["ref_mode"] = "encoded"

    report = validate_study(study)

    assert report.valid is True
    finding = next(
        w
        for w in report.warnings
        if w.code == "destination.thinned_ref_without_mapping"
    )
    assert "'main'" in finding.message


def test_a_thinned_ref_is_fine_when_an_extraction_conf_reads_the_mapping():
    study = valid_study()
    study["destinations"][0]["ref_mode"] = "encoded"
    study["inference_data"]["data_sources"]["fly"]["extraction_confs"].append(
        {
            "location": "metadata",
            "mapping": "ad_table_lookup",
            "key": "vt",
            "name": "stratum_gender",
            "functions": [],
            "value_type": "categorical",
            "aggregate": "last",
        }
    )

    assert validate_study(study).warnings == []


def test_the_thinned_ref_check_agrees_with_the_study_conf_function():
    study = valid_study()
    study["destinations"][0]["ref_mode"] = "encoded"

    conf = study_conf_from_sections(study)
    assert thins_its_ref_without_reading_the_mapping(conf) == ["main"]

    report = validate_study(study)
    assert "destination.thinned_ref_without_mapping" in codes(report.warnings)


def test_the_two_log_only_warnings_still_log(caplog):
    # The run path is unchanged: these are still logging.warning calls on the
    # optimize path, and validation is additive rather than a replacement.
    study = study_conf_from_sections(
        broken(
            destinations=[
                {
                    "type": "messenger",
                    "name": "main",
                    "initial_shortcode": "abc123",
                    "welcome_message": "hello",
                    "button_text": "Start",
                    "ref_mode": "encoded",
                },
                {
                    "type": "web",
                    "name": "site",
                    "url_template": "https://example.com/?ref={ref}",
                    "ref_mode": "encoded",
                },
            ]
        )
    )

    with caplog.at_level("WARNING"):
        warn_on_incomplete_targeting(study)
        warn_on_thinned_ref_without_mapping(study)

    assert "no longer carry stratum metadata" in caplog.text


# ---------------------------------------------------------------------------
# Never raises
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sections",
    [
        {},
        {"general": None},
        {"general": "a string"},
        {"strata": [None]},
        {"audiences": [{}]},
        {"inference_data": {"data_sources": {"fly": "nope"}}},
        {"recruitment": []},
        {"destinations": [{"type": "unknown-type", "name": "x"}]},
        {"creatives": [{"name": "x", "destination": "y", "template": None}]},
    ],
)
def test_validate_study_never_raises(sections):
    # The endpoint returns 200 with the report even for a broken study, so
    # anything that escapes here becomes a 500 for input the report exists to
    # describe.
    report = validate_study(sections)
    assert report.valid is False
