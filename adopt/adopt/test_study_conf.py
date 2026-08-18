from datetime import datetime, timedelta
from typing import Literal

import pytest
from pydantic import ValidationError

from .study_conf import (
    MULTI_DESTINATION_ENV_VAR,
    CreativeConf,
    DestinationRecruitmentExperiment,
    ExtractionConf,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    GeneralConf,
    InferenceDataConf,
    InvalidConfigError,
    PipelineRecruitmentExperiment,
    QuestionTargeting,
    SimpleRecruitment,
    SourceExtractionConf,
    StratumConf,
    StudyConf,
    TargetVar,
    UserInfo,
    disagreeing_token_keys,
    missing_targeting_variables,
    normalize_whatsapp_phone_number,
    ref_value,
    thins_its_ref_without_reading_the_mapping,
    unsafe_whatsapp_ref_tokens,
    whatsapp_phone_number_valid,
    whatsapp_ref_token_safe,
    whatsapp_shortcode_safe,
    supplied_variables,
    targeting_variables,
)


def _dt(day, month=1, year=2022, hour=0, minute=0):
    return datetime(year, month, day, hour=hour, minute=minute)


def _simple(
    name="foo",
    start_date=_dt(1),
    end_date=_dt(3),
    objective="objective",
    optimization_goal="goal",
    destination_type="destination",
    min_budget=1,
):
    return SimpleRecruitment(
        ad_campaign_name=name,
        objective=objective,
        optimization_goal=optimization_goal,
        destination_type=destination_type,
        min_budget=min_budget,
        start_date=start_date,
        end_date=end_date,
        budget=10,
        max_sample=100,
    )


def _pipeline(
    name="foo",
    budget_per_arm=10,
    max_sample_per_arm=100,
    start_date=_dt(1),
    end_date=_dt(5),
    arms=2,
    recruitment_days=2,
    offset_days=2,
    objective="objective",
    optimization_goal="goal",
    destination_type="destination",
    min_budget=1,
):
    return PipelineRecruitmentExperiment(
        ad_campaign_name_base=name,
        objective=objective,
        optimization_goal=optimization_goal,
        destination_type=destination_type,
        min_budget=min_budget,
        budget_per_arm=budget_per_arm,
        max_sample_per_arm=max_sample_per_arm,
        start_date=start_date,
        end_date=end_date,
        arms=arms,
        recruitment_days=recruitment_days,
        offset_days=offset_days,
    )


def _destination(
    name="foo",
    budget_per_arm=10,
    max_sample_per_arm=100,
    start_date=_dt(1),
    end_date=_dt(3),
    destinations=["baz", "qux"],
    objective="objective",
    optimization_goal="goal",
    destination_type="destination",
    min_budget=1,
):
    return DestinationRecruitmentExperiment(
        ad_campaign_name_base=name,
        objective=objective,
        optimization_goal=optimization_goal,
        destination_type=destination_type,
        min_budget=min_budget,
        budget_per_arm=budget_per_arm,
        max_sample_per_arm=max_sample_per_arm,
        start_date=start_date,
        end_date=end_date,
        destinations=destinations,
    )


# def test_get_campaign_names_gets_base_when_not_experiment():
#     assert get_campaign_names("foo-bar", None) == ["foo-bar"]


def test_simple_recruitment_campaign_names_is_base_name():
    re = _simple("foo", _dt(1), _dt(3))
    assert re.campaign_names == ["foo"]


def test_pipeline_recruitment_names_has_suffix_of_arm_number():
    re = _pipeline()
    assert re.campaign_names == ["foo-1", "foo-2"]


def test_destination_recruitment_names_has_suffix_of_destination():
    re = _destination()
    assert re.campaign_names == ["foo-baz", "foo-qux"]


def test_pipeline_recruitment_opt_budget_is_same_as_per_arm():
    re = _pipeline()
    assert re.opt_budget == 10


def test_destination_recruitment_opt_budget_is_multiplied_by_arms():
    re = _destination()
    assert re.opt_budget == 20


from datetime import datetime

from .study_conf import Stratum

# strata: list[Union[Stratum, StratumConf]],
# min_budget: float,
# end_date: datetime,
# budget: Optional[Budget],
# now: datetime,


def _strat(id_, quota=0.5):
    return Stratum(
        id=id_,
        quota=quota,
        creatives=[],
        facebook_targeting={},
        question_targeting={
            "op": "answered",
            "vars": [{"type": "variable", "value": "rand"}],
        },
        metadata={},
    )


def test_simple_spend_for_day_returns_base_budget_when_no_budget_proposal():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]
    start = _dt(1)
    end = _dt(10)
    now = _dt(5)

    r = _simple("study", start, end)
    res = r.spend_for_day(strata, 1, None, now)
    assert res == {"study": {"foo": 1.0, "bar": 1.0, "baz": 1.0}}


def test_simple_spend_for_day_returns_budget_proposal_when_one_day_left():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(9)
    r = _simple("study", start, end)
    budget = {"foo": 3.0, "bar": 1.0, "baz": 5.0}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": budget}


def test_simple_spend_for_day_returns_budget_proposal_when_less_than_one_day_left():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(9, hour=12)

    r = _simple("study", start, end)
    budget = {"foo": 3.0, "bar": 1.0, "baz": 5.0}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": budget}


def test_simple_spend_for_day_returns_budget_proposal_spread_over_days_and_floored():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(8)
    r = _simple("study", start, end)

    budget = {"foo": 2.2, "bar": 2.0, "baz": 3.51}  # quite a bit under budget!
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": {"foo": 1.10, "bar": 1.0, "baz": 1.75}}


def test_simple_spend_for_day_puts_budget_to_zero_if_under_min_budget():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(9)
    r = _simple("study", start, end)

    budget = {"foo": 1.0, "bar": 0.5, "baz": 1.0}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": {"foo": 1.0, "bar": 0.0, "baz": 1.0}}


def test_simple_spend_for_day_sets_budget_to_zero_if_no_more_days():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(10)
    r = _simple("study", start, end)

    budget = {"foo": 1.0, "bar": 0.5, "baz": 1.0}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": {"foo": 0.0, "bar": 0.0, "baz": 0.0}}


def test_destination_spend_for_day_returns_base_budget_when_no_budget_proposal():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(2)
    now = _dt(1)

    r = _destination("study", start_date=start, end_date=end)
    res = r.spend_for_day(strata, 1, None, now)

    assert res == {
        "study-baz": {"foo": 1.0, "bar": 1.0, "baz": 1.0},
        "study-qux": {"foo": 1.0, "bar": 1.0, "baz": 1.0},
    }


def test_destination_spend_for_day_returns_budget_proposal_split_when_one_day_left():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(2)
    now = _dt(1)

    r = _destination("study", start_date=start, end_date=end)
    budget = {"foo": 4.31, "bar": 8.00, "baz": 13.51}

    res = r.spend_for_day(strata, 1, budget, now)

    assert res == {
        "study-baz": {"foo": 2.15, "bar": 4.0, "baz": 6.75},
        "study-qux": {"foo": 2.15, "bar": 4.0, "baz": 6.75},
    }


def test_destination_spend_for_day_returns_proposal_spread_over_days_and_floored():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(3)
    now = _dt(1)

    r = _destination("study", start_date=start, end_date=end)
    budget = {"foo": 4.3, "bar": 8.0, "baz": 13.5}

    res = r.spend_for_day(strata, 1, budget, now)

    assert res == {
        "study-baz": {"foo": 1.07, "bar": 2.0, "baz": 3.37},
        "study-qux": {"foo": 1.07, "bar": 2.0, "baz": 3.37},
    }


def test_pipeline_pick_active_campaign_picks_first_campaign_at_start():
    start = _dt(1)
    now = _dt(1)
    r = _pipeline(
        name="foo", start_date=start, arms=2, recruitment_days=2, offset_days=2
    )
    assert r.current_campaign(now) == (0, 2)


def test_pipeline_pick_active_campaign_picks_no_campaign_if_between_waves():
    start = _dt(1)
    now = _dt(4)
    end = _dt(7)

    r = _pipeline(
        name="foo",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=4,
    )
    assert r.current_campaign(now) == (None, None)


def test_pipeline_pick_active_campaign_picks_next_campaign_when_it_starts():
    start = _dt(1)
    now = _dt(5)
    end = _dt(7)

    r = _pipeline(
        name="foo",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=4,
    )
    assert r.current_campaign(now) == (1, 2)


def test_pipeline_pick_active_campaign_stops_when_finished():
    start = _dt(1)
    now = _dt(9)
    end = _dt(7)

    r = _pipeline(
        name="foo",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=4,
    )
    assert r.current_campaign(now) == (None, None)


def test_pipeline_pick_active_campaign_keeps_going_recruitment_days_and_offset_same():
    start = _dt(1)
    now = _dt(3)
    end = _dt(5)

    r = _pipeline(
        name="foo",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=2,
    )
    assert r.current_campaign(now) == (1, 2)


def test_pipeline_spend_for_day_sets_budget_to_zero_if_no_more_days():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]
    start = _dt(1)
    now = _dt(10)
    end = _dt(7)

    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=4,
    )

    budget = {"foo": 1.0, "bar": 0.5, "baz": 1.0}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }


def test_pipeline_spend_for_day_sets_budget_to_base_if_no_budget():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]
    start = _dt(1)
    now = _dt(1)
    end = _dt(7)

    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=2,
        offset_days=4,
    )

    res = r.spend_for_day(strata, 1, None, now)
    assert res == {
        "study-1": {"foo": 1.0, "bar": 1.0, "baz": 1.0},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }


def test_pipeline_spend_for_day_sets_to_budget_for_on_campaign_based_on_days_left():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]
    start = _dt(1)
    now = _dt(1)
    end = _dt(10)

    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=3,
        offset_days=6,
    )

    budget = {"foo": 9.0, "bar": 12.0, "baz": 13.7}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 3.0, "bar": 4.0, "baz": 4.56},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }

    budget = {"foo": 6.0, "bar": 8.0, "baz": 9.7}
    now = _dt(2)
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 3.0, "bar": 4.0, "baz": 4.84},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }

    now = _dt(8)
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
        "study-2": {"foo": 3.0, "bar": 4.0, "baz": 4.84},
    }


def test_pipeline_spend_can_check_validity_of_end_date():
    start = _dt(1)
    end = _dt(10)

    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=3,
        offset_days=6,
    )

    r.validate_dates()

    start = _dt(1)
    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=3,
        recruitment_days=3,
        offset_days=3,
    )

    r.validate_dates()

    with pytest.raises(Exception):
        r = _pipeline(
            name="study",
            start_date=start,
            end_date=end,
            arms=3,
            recruitment_days=3,
            offset_days=5,
        )
        r.validate_dates()


def test_pipeline_get_inference_window():
    start = _dt(1)
    now = _dt(1)
    end = _dt(10)

    r = _pipeline(
        name="study",
        start_date=start,
        end_date=end,
        arms=2,
        recruitment_days=3,
        offset_days=6,
    )

    inf_start, inf_end = r.get_inference_window(now)

    assert inf_start == start
    assert inf_end == start + timedelta(days=3)

    now = _dt(7)
    inf_start, inf_end = r.get_inference_window(now)

    assert inf_start == start + timedelta(days=6)
    assert inf_end == inf_start + timedelta(days=3)


# ---------------------------------------------------------------------------
# Completeness check (A6): strata that target variables nothing supplies.
#
# A question_targeting predicate reads variables swoosh writes into
# inference_data, and swoosh writes exactly what the inference_data confs name.
# A predicate naming anything else can never match — the stratum counts zero and
# the optimizer moves its budget away from a segment that may be recruiting
# fine. It does not error, which is why it needs detecting.
# ---------------------------------------------------------------------------


def _study_with(targeting, inference_data):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[],
        audiences=[],
        creatives=[],
        strata=[
            StratumConf(
                id="stratum-1",
                quota=1.0,
                creatives=[],
                audiences=[],
                excluded_audiences=[],
                facebook_targeting={},
                question_targeting=targeting,
                metadata={},
            )
        ],
        recruitment=_simple(),
        inference_data=inference_data,
    )


def _extraction_conf(name, location="metadata", key="gender", mapping="raw"):
    return ExtractionConf(
        location=location,
        mapping=mapping,
        key=key,
        name=name,
        functions=[],
        value_type="categorical",
        aggregate="first",
    )


def _lookup_conf(stratum_var, key="vt"):
    """One ad-derived variable: read the token at `key`, pull `stratum_var`.

    Note that `name` is the stratum variable, because for a lookup it does
    double duty -- output name and row key both.
    """
    return _extraction_conf(
        stratum_var, location="metadata", key=key, mapping="ad_table_lookup"
    )


def _inference_conf(*names):
    return InferenceDataConf(
        data_sources={
            "fly": SourceExtractionConf(
                extraction_confs=[_extraction_conf(n) for n in names]
            )
        }
    )


def _targeting(*variables):
    return QuestionTargeting(
        op="and",
        vars=[
            QuestionTargeting(
                op="equal",
                vars=[
                    TargetVar(type="variable", value=v),
                    TargetVar(type="constant", value="women"),
                ],
            )
            for v in variables
        ],
    )


def test_targeting_variables_walks_nested_predicates():
    # vars holds either leaves or nested predicates, and real strata nest.
    assert targeting_variables(_targeting("md:gender", "md:age")) == {
        "md:gender",
        "md:age",
    }


def test_targeting_variables_ignores_constants():
    # Only type == "variable" names a variable; constants are the compared-to
    # values and must not be mistaken for one.
    t = QuestionTargeting(
        op="equal",
        vars=[
            TargetVar(type="variable", value="md:gender"),
            TargetVar(type="constant", value="md:not_a_variable"),
        ],
    )
    assert targeting_variables(t) == {"md:gender"}


def test_targeting_variables_of_nothing_is_empty():
    assert targeting_variables(None) == set()


def test_supplied_variables_spans_every_location_and_mapping():
    # What matters to a predicate is that the variable exists, not where it
    # came from -- so a lookup conf supplies just as a raw one does.
    conf = InferenceDataConf(
        data_sources={
            "fly": SourceExtractionConf(
                extraction_confs=[
                    _lookup_conf("gender"),
                    _extraction_conf("q1", location="variable"),
                ]
            )
        }
    )
    assert supplied_variables(conf) == {"gender", "q1"}


def test_no_gap_when_every_targeted_variable_is_supplied():
    study = _study_with(
        targeting=_targeting("md:gender"),
        inference_data=_inference_conf("md:gender"),
    )
    assert missing_targeting_variables(study) == {}


def test_gap_is_reported_per_stratum():
    study = _study_with(
        targeting=_targeting("md:gender", "md:region"),
        inference_data=_inference_conf("md:gender"),
    )
    assert missing_targeting_variables(study) == {"stratum-1": {"md:region"}}


def test_lookup_confs_satisfy_targeting():
    # A new study moves its stratum variable onto the ad table. The predicate
    # is unchanged and must still be considered satisfied, because the variable
    # name is what a predicate matches on.
    #
    # Note the predicate targets "gender", not "md:gender": for a lookup, name
    # is the stratum variable, so the output is named after what it pulls.
    study = _study_with(
        targeting=_targeting("gender"),
        inference_data=InferenceDataConf(
            data_sources={"fly": SourceExtractionConf(extraction_confs=[_lookup_conf("gender")])}
        ),
    )
    assert missing_targeting_variables(study) == {}


def test_study_with_no_inference_conf_reports_every_targeted_variable():
    # Detected, but the caller only warns: a study with no inference_data conf
    # is usually one that is not finished being configured, not a broken one.
    study = _study_with(targeting=_targeting("md:gender"), inference_data=None)
    assert missing_targeting_variables(study) == {"stratum-1": {"md:gender"}}


def test_stratum_with_no_targeting_never_reports_a_gap():
    study = _study_with(targeting=None, inference_data=None)
    assert missing_targeting_variables(study) == {}


# ---------------------------------------------------------------------------
# Click-to-WhatsApp destinations (A8): config-time ref validation.
#
# fly recovers the shortcode on WhatsApp from the ad's autofill text, matched
# against an anchored full-match pattern of [A-Za-z0-9_-] tokens. A ref that
# fails it does not error -- fly derives no conversation_started and the arrival
# falls through to FALLBACK_FORM, a real survey whose users look like
# completions. So an undeliverable ref has to be rejected when the study is
# configured, never emitted and hoped for.
# ---------------------------------------------------------------------------


# Real values from production study confs, quoted in
# planning/ad-id-attribution.md. Half of them are undeliverable, which is the
# finding that makes full-ref mode a rarity rather than a default.
PRODUCTION_SAFE = ["3B", "gelangchoice", "women", "Smiling", "location"]

# Undeliverable under the old narrow gate; deliverable now, once encoded.
PRODUCTION_ONCE_UNSAFE = [
    "Static English - Girls",
    "Bauchi State",
    "Like Parents",
    "South East",
]


def test_every_recorded_production_value_is_now_deliverable():
    # It was 5 of 9. fly widened the entry gate to accept percent-encoded
    # octets, so encoding now carries a space through and the values that
    # could not be shipped at all now can.
    for v in PRODUCTION_SAFE + PRODUCTION_ONCE_UNSAFE:
        assert whatsapp_ref_token_safe(v), v


def test_percent_encoding_now_rescues_a_spaced_value():
    # The inverse of what this asserted under the old gate. Encoding used to
    # trade one undeliverable token for another, because `%` was not in the
    # alphabet either; now it is.
    assert whatsapp_ref_token_safe("Bauchi State")
    assert ref_value("Bauchi State") == "Bauchi%20State"


def test_a_slash_is_the_one_residual_that_still_fails():
    # `quote()` keeps "/" literal by default and the gate does not accept it.
    # It does not corrupt anything -- it is caught at config time -- but it is
    # the only character a value still cannot contain.
    assert not whatsapp_ref_token_safe("North/South")


def test_unsafe_tokens_reports_keys_as_well_as_values():
    # Both sides become dot-separated tokens, so a key with a space breaks the
    # ref just as a value does.
    assert unsafe_whatsapp_ref_tokens({"gender": "women"}) == []
    assert unsafe_whatsapp_ref_tokens({"gender": "Bauchi State"}) == []
    assert unsafe_whatsapp_ref_tokens({"gender": "North/South"}) == [
        "gender=North/South"
    ]
    assert unsafe_whatsapp_ref_tokens({"my/key": "women"}) == ["my/key=women"]


def _whatsapp_destination(shortcode="mnchweek", full_ref=False):
    return FlyWhatsAppDestination(
        type="whatsapp",
        name="whatsapp",
        initial_shortcode=shortcode,
        welcome_message="Tap send to start",
        whatsapp_phone_number="+1-541-920-2635",
        include_metadata_in_ref=full_ref,
    )


def _whatsapp_study(metadata, full_ref=False, destination_name="whatsapp"):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[_whatsapp_destination(full_ref=full_ref)],
        audiences=[],
        creatives=[
            CreativeConf(destination=destination_name, name="Smiling", template={})
        ],
        strata=[
            StratumConf(
                id="stratum-1",
                quota=1.0,
                creatives=["Smiling"],
                audiences=[],
                excluded_audiences=[],
                facebook_targeting={},
                metadata=metadata,
            )
        ],
        recruitment=_simple(destination_type="WHATSAPP"),
    )


def test_unsafe_shortcode_is_rejected_on_the_destination_itself():
    # Applies in both modes: even the default token is `form.<shortcode>`.
    #
    # And the shortcode keeps the NARROW alphabet even though the widened gate
    # would accept it encoded. A shortcode is shareable by design -- someone
    # texts `form.<shortcode>` straight into WhatsApp by hand, and a hand-typed
    # space is a literal space, not %20. It has to be typeable, not merely
    # encodable.
    with pytest.raises(InvalidConfigError, match="initial_shortcode"):
        _whatsapp_destination(shortcode="mnch week")


def test_a_metadata_value_may_contain_what_a_shortcode_may_not():
    # The asymmetry, stated directly: values are only ever carried by an ad.
    assert whatsapp_ref_token_safe("mnch week")
    assert not whatsapp_shortcode_safe("mnch week")


def test_safe_shortcodes_are_accepted():
    for shortcode in ["mnchweek", "mnch_week", "mnch-week-2", "MNCH2"]:
        assert _whatsapp_destination(shortcode=shortcode).initial_shortcode == shortcode


def test_full_ref_with_spaced_stratum_metadata_is_now_accepted():
    # This used to raise. The widened gate plus encoding is exactly what
    # unblocked it, and it is the single biggest practical change from D1.
    study = _whatsapp_study({"State": "Bauchi State"}, full_ref=True)
    assert study.strata[0].metadata["State"] == "Bauchi State"


def test_full_ref_with_a_genuinely_undeliverable_value_is_still_rejected():
    with pytest.raises(InvalidConfigError, match="North/South"):
        _whatsapp_study({"Region": "North/South"}, full_ref=True)


def test_full_ref_with_safe_stratum_metadata_is_accepted():
    study = _whatsapp_study({"gender": "women", "creative": "3B"}, full_ref=True)
    assert study.strata[0].metadata["gender"] == "women"


def test_shortcode_only_tolerates_metadata_it_never_ships():
    """The reason shortcode-only is the default.

    The same stratum that cannot have a full ref is perfectly fine on the
    default setting, because none of those values travel in the autofill text.
    The optimizer still gets the stratum via the ad-ID join.
    """
    study = _whatsapp_study({"State": "Bauchi State"}, full_ref=False)
    assert study.strata[0].metadata["State"] == "Bauchi State"


def test_full_ref_ignores_strata_that_do_not_publish_through_that_destination():
    # A stratum whose creatives all point elsewhere never produces a WhatsApp
    # ref, so its metadata cannot break one.
    study = _whatsapp_study(
        {"State": "Bauchi State"}, full_ref=True, destination_name="somewhere-else"
    )
    assert study.strata[0].metadata["State"] == "Bauchi State"


def test_full_ref_validation_covers_the_form_key_and_extra_metadata():
    # `form` is folded in from the shortcode, which is already validated, but
    # extra_metadata is not -- and it rides in the ref too.
    study = _whatsapp_study({"gender": "women"}, full_ref=True)
    study_dict = study.model_dump()
    study_dict["general"]["extra_metadata"] = {"country": "Sierra/Leone"}

    with pytest.raises(InvalidConfigError, match="Sierra/Leone"):
        StudyConf(**study_dict)


def test_a_study_with_no_whatsapp_destination_is_never_checked():
    # Every existing study, in other words.
    study = _study_with(targeting=None, inference_data=None)
    assert study.strata[0].metadata == {}


# ---------------------------------------------------------------------------
# WhatsApp phone number and destination_type (A9).
# ---------------------------------------------------------------------------


def test_phone_number_normalises_to_digits():
    # Meta's promoted_object reference types whatsapp_phone_number as a numeric
    # string, while credentials store the display form. Measured by ctwa_probe.
    assert normalize_whatsapp_phone_number("+1-541-920-2635") == "15419202635"
    assert normalize_whatsapp_phone_number("(541) 920 2635") == "5419202635"
    assert normalize_whatsapp_phone_number("15419202635") == "15419202635"


def test_phone_number_validity_follows_e164_bounds():
    assert whatsapp_phone_number_valid("+1-541-920-2635")
    assert not whatsapp_phone_number_valid("")
    assert not whatsapp_phone_number_valid("123456")  # too short
    assert not whatsapp_phone_number_valid("1" * 16)  # past E.164's 15
    assert not whatsapp_phone_number_valid("not-a-number")


def test_malformed_phone_number_is_rejected_at_config_time():
    # Fails while someone is configuring the study, not when Meta rejects the
    # ad set on the next reconciliation run.
    with pytest.raises(InvalidConfigError, match="dialable"):
        FlyWhatsAppDestination(
            type="whatsapp",
            name="whatsapp",
            initial_shortcode="mnchweek",
            welcome_message="Hi",
            whatsapp_phone_number="123",
        )


def test_a_phone_number_id_pasted_instead_of_a_number_is_rejected():
    # The trap ctwa_probe calls out by name: phone_number_id is not the number,
    # and sending it is "an easy way to spend a day testing the wrong number".
    # A 17-digit id exceeds E.164, so it is caught.
    with pytest.raises(InvalidConfigError, match="phone_number_id"):
        FlyWhatsAppDestination(
            type="whatsapp",
            name="whatsapp",
            initial_shortcode="mnchweek",
            welcome_message="Hi",
            whatsapp_phone_number="10925130295730592",
        )


def test_the_destination_exposes_the_number_in_metas_shape():
    d = _whatsapp_destination()
    assert d.promoted_phone_number == "15419202635"


def test_whatsapp_destination_with_a_messenger_destination_type_is_rejected():
    """Meta routes by destination_type, so this ad would never reach WhatsApp.

    Nothing downstream notices: the creative is valid and the promoted_object
    is set. The ad simply does not do what the study thinks it does.
    """
    study = _whatsapp_study({"gender": "women"}).model_dump()
    study["recruitment"]["destination_type"] = "MESSENGER"

    with pytest.raises(InvalidConfigError, match="destination_type"):
        StudyConf(**study)


def test_a_whatsapp_only_study_accepts_exactly_the_whatsapp_destination_type():
    """WHATSAPP is what a WhatsApp destination implies, so WHATSAPP is what it takes."""
    study = _whatsapp_study({"gender": "women"}).model_dump()
    study["recruitment"]["destination_type"] = "WHATSAPP"

    assert StudyConf(**study).recruitment.destination_type == "WHATSAPP"


def test_a_whatsapp_only_study_with_a_combination_destination_type_is_rejected():
    """The second silent hole, closed. This used to pass.

    The old check asked only whether destination_type was WhatsApp-*capable*,
    so every combination token sailed through on a study with nothing but
    WhatsApp destinations. Meta then runs the ad set multi-destination: the
    WhatsApp arm works, and the Messenger (or Instagram) arm has no destination
    behind it and therefore no routing token at all. Everyone Meta sends to that
    arm starts a conversation and falls through to FALLBACK_FORM -- a real
    survey, so they look like completions rather than errors, which is exactly
    how VIR-19 stayed invisible for four days.

    Half the ad works, which is why nobody notices. Hence: fail at config time.
    """
    for destination_type in [
        "MESSAGING_MESSENGER_WHATSAPP",
        "MESSAGING_INSTAGRAM_DIRECT_WHATSAPP",
        "MESSAGING_INSTAGRAM_DIRECT_MESSENGER_WHATSAPP",
    ]:
        study = _whatsapp_study({"gender": "women"}).model_dump()
        study["recruitment"]["destination_type"] = destination_type

        with pytest.raises(InvalidConfigError, match="none of its destinations"):
            StudyConf(**study)


def test_destination_type_is_not_checked_for_studies_without_whatsapp():
    # Every existing study: destination_type stays whatever it was.
    study = _study_with(targeting=None, inference_data=None)
    assert study.recruitment.destination_type == "destination"


# ---------------------------------------------------------------------------
# Thinning the ref without reading the mapping (A4).
#
# include_metadata_in_ref off only works if the study also reads the ad ->
# stratum mapping. One without the other leaves the study with no attribution
# at all -- the ref no longer carries the stratum and nothing looks the ad up.
# ---------------------------------------------------------------------------


def _messenger_study(include_metadata_in_ref, inference_data=None):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[
            FlyMessengerDestination(
                type="messenger",
                name="messenger",
                initial_shortcode="mnchweek",
                welcome_message="Welcome!",
                button_text="OK",
                include_metadata_in_ref=include_metadata_in_ref,
            )
        ],
        audiences=[],
        creatives=[CreativeConf(destination="messenger", name="Smiling", template={})],
        strata=[],
        recruitment=_simple(),
        inference_data=inference_data,
    )


def test_a_full_ref_study_is_never_flagged():
    # Every existing study.
    assert thins_its_ref_without_reading_the_mapping(_messenger_study(True)) == []


def test_thinning_the_ref_with_no_ad_confs_is_flagged():
    study = _messenger_study(False, _inference_conf("md:gender"))
    assert thins_its_ref_without_reading_the_mapping(study) == ["messenger"]


def test_thinning_the_ref_with_a_lookup_conf_is_fine():
    conf = InferenceDataConf(
        data_sources={"fly": SourceExtractionConf(extraction_confs=[_lookup_conf("gender")])}
    )
    assert thins_its_ref_without_reading_the_mapping(_messenger_study(False, conf)) == []


# ---------------------------------------------------------------------------
# The mapping field itself.


def test_mapping_defaults_to_raw():
    # The default is the historical behaviour, which is what lets every conf
    # written before this field existed keep meaning what it meant.
    assert _extraction_conf("md:gender").mapping == "raw"
    assert _extraction_conf("md:gender").is_ad_table_lookup is False


def test_location_ad_is_rejected():
    # The deprecated ad_id join. It fails closed rather than loading into a
    # study swoosh can no longer resolve, which would count zero and reallocate
    # budget on empty data, silently.
    with pytest.raises(ValidationError) as e:
        _extraction_conf("md:gender", location="ad")

    assert "ad_table_lookup" in str(e.value), "the error must name the replacement"


def test_a_lookup_on_a_variable_is_rejected():
    # The token is stamped by fly, not answered by the respondent, so this
    # cannot mean anything. Rejected rather than ignored because of what `key`
    # would then be taken for: swoosh reads a lookup conf's key as the
    # declaration of where the token lives, and one stray conf would have every
    # respondent in the study checked against the wrong metadata key -- which
    # reads as an organic arrival and does not alarm.
    with pytest.raises(ValidationError) as e:
        _extraction_conf("q1", location="variable", mapping="ad_table_lookup")

    assert "metadata" in str(e.value)


def test_an_unknown_mapping_is_rejected():
    with pytest.raises(ValidationError):
        _extraction_conf("md:gender", mapping="ad_id_lookup")


def test_lookup_confs_agreeing_on_the_token_key_is_not_a_disagreement():
    study = _study_with(
        targeting=None,
        inference_data=InferenceDataConf(
            data_sources={
                "fly": SourceExtractionConf(
                    extraction_confs=[_lookup_conf("gender"), _lookup_conf("Age")]
                )
            }
        ),
    )
    assert disagreeing_token_keys(study) == {}


def test_lookup_confs_reading_different_token_keys_are_flagged():
    # One respondent has one token, in one place. Confs on the other key
    # attribute nobody -- and silently, because a token that is not there looks
    # exactly like an organic arrival.
    study = _study_with(
        targeting=None,
        inference_data=InferenceDataConf(
            data_sources={
                "fly": SourceExtractionConf(
                    extraction_confs=[
                        _lookup_conf("gender", key="vt"),
                        _lookup_conf("Age", key="tok"),
                    ]
                )
            }
        ),
    )
    assert disagreeing_token_keys(study) == {"fly": ["tok", "vt"]}


def test_a_raw_conf_on_another_key_is_not_a_disagreement():
    # Only lookup confs read the token. A raw conf reading some other metadata
    # key is ordinary and must not be dragged into this.
    study = _study_with(
        targeting=None,
        inference_data=InferenceDataConf(
            data_sources={
                "fly": SourceExtractionConf(
                    extraction_confs=[
                        _lookup_conf("gender", key="vt"),
                        _extraction_conf("md:city", key="city"),
                    ]
                )
            }
        ),
    )
    assert disagreeing_token_keys(study) == {}


def test_thinning_the_ref_with_no_inference_conf_at_all_is_flagged():
    assert thins_its_ref_without_reading_the_mapping(
        _messenger_study(False, None)
    ) == ["messenger"]


def test_a_thinned_whatsapp_destination_is_flagged_the_same_way():
    # Same concept, same field, same failure -- so the check spans both fly
    # destination types rather than being Messenger-specific.
    study = _whatsapp_study({"gender": "women"}, full_ref=False)
    assert thins_its_ref_without_reading_the_mapping(study) == ["whatsapp"]


# ---------------------------------------------------------------------------
# destination_type as a claim about the channel, and multi-destination.
#
# `destination_type` used to be checked in exactly one direction -- a WhatsApp
# destination had to sit on a WhatsApp-capable ad set -- so two mirror cases
# passed silently, both of them producing an ad where one arm routes and the
# other quietly recruits into FALLBACK_FORM.
# ---------------------------------------------------------------------------


def _messenger_only_study(destination_type):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[
            FlyMessengerDestination(
                type="messenger",
                name="messenger",
                initial_shortcode="mnchweek",
                welcome_message="Welcome!",
                button_text="OK",
            )
        ],
        audiences=[],
        creatives=[
            CreativeConf(destination="messenger", name="Smiling", template={})
        ],
        strata=[],
        recruitment=_simple(destination_type=destination_type),
    )


def test_a_messenger_only_study_with_a_multi_destination_type_is_rejected():
    """The first silent hole, closed. This used to build happily.

    MESSAGING_MESSENGER_WHATSAPP with only Messenger destinations runs the ads
    multi-destination: the Messenger arm keeps its quick-reply welcome message
    and routes fine, and the WhatsApp arm has no autofill token at all. Every
    WhatsApp clicker Meta routes there lands on FALLBACK_FORM -- a real survey
    belonging to a real researcher.

    Half the ad works, which is exactly why the study's operator has no reason
    to suspect it. fly's own onboarding doc calls this "the single easiest way
    to misconfigure a WhatsApp ad".
    """
    with pytest.raises(InvalidConfigError, match="none of its destinations"):
        _messenger_only_study("MESSAGING_MESSENGER_WHATSAPP")


def test_a_messenger_only_study_with_a_whatsapp_destination_type_is_rejected():
    with pytest.raises(InvalidConfigError, match="none of its destinations"):
        _messenger_only_study("WHATSAPP")


def test_a_messenger_only_study_with_messenger_is_accepted():
    """The 110 production studies. Untouched."""
    study = _messenger_only_study("MESSENGER")
    assert study.recruitment.destination_type == "MESSENGER"


def test_a_non_messaging_destination_type_makes_no_claim_to_check():
    """WEB with Messenger destinations still builds.

    Two production studies are configured exactly this way (both ended in 2024,
    measured 2026-08-17). A non-messaging destination_type is not a claim about
    which messaging app opens, so there is nothing to contradict; the ad set's
    value is derived from the destinations instead.
    """
    assert _messenger_only_study("WEB").recruitment.destination_type == "WEB"


def _multi_study(destination_type="MESSAGING_MESSENGER_WHATSAPP",
                 optimization_goal="CONVERSATIONS"):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=[
            FlyMultiDestination(
                type="multi",
                name="multi",
                initial_shortcode="mnchweek",
                welcome_message="Tap below or send to start",
                button_text="Start survey",
                whatsapp_phone_number="+1-541-920-2635",
            )
        ],
        audiences=[],
        creatives=[CreativeConf(destination="multi", name="Smiling", template={})],
        strata=[],
        recruitment=_simple(
            destination_type=destination_type, optimization_goal=optimization_goal
        ),
    )


@pytest.fixture
def multi_enabled(monkeypatch):
    monkeypatch.setenv(MULTI_DESTINATION_ENV_VAR, "true")


def test_a_multi_destination_needs_the_multi_destination_type(multi_enabled):
    assert _multi_study().recruitment.destination_type == (
        "MESSAGING_MESSENGER_WHATSAPP"
    )

    with pytest.raises(InvalidConfigError, match="none of its destinations"):
        _multi_study(destination_type="MESSENGER")

    with pytest.raises(InvalidConfigError, match="none of its destinations"):
        _multi_study(destination_type="WHATSAPP")


def test_multi_destination_requires_the_conversations_optimization_goal(multi_enabled):
    """Meta's constraint, validated where someone can still act on it.

    Multi-destination forces optimization_goal CONVERSATIONS -- strictly
    narrower than single-destination CTWA -- which couples a destination choice
    to a study-level recruitment setting. Checked rather than silently
    overridden: optimization_goal is what cost-per-respondent is measured
    against, and rewriting it would change what the study buys without saying so.
    """
    with pytest.raises(InvalidConfigError, match="CONVERSATIONS"):
        _multi_study(optimization_goal="LINK_CLICKS")

    with pytest.raises(InvalidConfigError, match="optimization_goal"):
        _multi_study(optimization_goal="IMPRESSIONS")


def test_the_conversations_check_names_both_fields(multi_enabled):
    """So the error is actionable. Meta's own rejection never mentions the
    destination, which is what makes this worth catching early."""
    try:
        _multi_study(optimization_goal="LINK_CLICKS")
    except InvalidConfigError as e:
        assert "optimization_goal" in str(e)
        assert "multi-destination" in str(e)
    else:
        raise AssertionError("expected the goal check to refuse")


def test_the_conversations_check_leaves_other_studies_alone():
    """Only multi is constrained. Single-destination CTWA accepts LINK_CLICKS,
    and must keep doing so -- a Page subject to European privacy rules cannot
    use CONVERSATIONS for click-to-WhatsApp at all."""
    study = _whatsapp_study({"gender": "women"}).model_dump()
    study["recruitment"]["optimization_goal"] = "LINK_CLICKS"

    assert StudyConf(**study).recruitment.optimization_goal == "LINK_CLICKS"


def test_a_multi_destination_shortcode_keeps_the_narrow_alphabet(multi_enabled):
    """It has a WhatsApp arm, so the shortcode must be typeable by hand.

    Someone who hears about the study texts `form.<shortcode>` straight into
    WhatsApp; a hand-typed space is a literal space, not %20, and lands them in
    the fallback survey.
    """
    with pytest.raises(InvalidConfigError, match="initial_shortcode"):
        FlyMultiDestination(
            type="multi",
            name="multi",
            initial_shortcode="mnch week",
            welcome_message="Hi",
            button_text="Start",
            whatsapp_phone_number="+1-541-920-2635",
        )


def test_a_multi_destination_number_must_be_dialable(multi_enabled):
    with pytest.raises(InvalidConfigError, match="dialable"):
        FlyMultiDestination(
            type="multi",
            name="multi",
            initial_shortcode="mnchweek",
            welcome_message="Hi",
            button_text="Start",
            whatsapp_phone_number="10925130295730592",
        )


def test_a_multi_destination_exposes_the_number_in_metas_shape(multi_enabled):
    dest = FlyMultiDestination(
        type="multi",
        name="multi",
        initial_shortcode="mnchweek",
        welcome_message="Hi",
        button_text="Start",
        whatsapp_phone_number="+1-541-920-2635",
    )
    assert dest.promoted_phone_number == "15419202635"


def test_a_thin_multi_ref_without_an_ad_conf_is_reported(multi_enabled):
    """include_metadata_in_ref defaults False on multi, so the ad -> stratum
    mapping is the only attribution it has. Reported for the same reason as the
    other fly destinations."""
    study = _multi_study()
    assert thins_its_ref_without_reading_the_mapping(study) == ["multi"]


# ---------------------------------------------------------------------------
# The dashboard contract.
#
# The destination forms in dashboard/src/pages/StudyConfPage/forms/destinations/
# POST these exact shapes. The two repos share no schema — the form builds a
# plain object and adopt parses it — so a field renamed on one side and not the
# other fails at study-save time for a researcher, with a pydantic error rather
# than anything actionable. These tests are the contract.
#
# Keep them in step with `emptyStates` in Destination.tsx.
# ---------------------------------------------------------------------------


def test_the_dashboard_whatsapp_form_shape_parses():
    """What Destination.tsx's `whatsapp` emptyState produces, once filled in."""
    from .study_conf import FlyWhatsAppDestination

    dest = FlyWhatsAppDestination(
        **{
            "name": "fly whatsapp",
            "initial_shortcode": "mnchweek",
            "welcome_message": "Tap send to start",
            "whatsapp_phone_number": "+1-541-920-2635",
            "type": "whatsapp",
        }
    )

    assert dest.type == "whatsapp"
    # Not sent by the form, and must therefore have a default. The WhatsApp
    # default is off: the autofill text is visible to and editable by the
    # respondent.
    assert dest.include_metadata_in_ref is False
    assert dest.additional_metadata is None


def test_the_dashboard_multi_form_shape_parses(multi_enabled):
    """What Destination.tsx's `multi` emptyState produces, once filled in."""
    dest = FlyMultiDestination(
        **{
            "name": "fly multi",
            "initial_shortcode": "mnchweek",
            "welcome_message": "Tap below or send to start",
            "button_text": "Start survey",
            "whatsapp_phone_number": "+1-541-920-2635",
            "type": "multi",
        }
    )

    assert dest.type == "multi"
    assert dest.include_metadata_in_ref is False


def test_the_dashboard_additional_metadata_shape_parses(multi_enabled):
    """The metadata text box sends a parsed object, or omits the key entirely.

    It never sends `{}` for a cleared field — additionalMetadata.ts maps an
    empty box to null — so both spellings have to work.
    """
    from .study_conf import FlyWhatsAppDestination

    base = {
        "name": "d",
        "initial_shortcode": "mnchweek",
        "welcome_message": "Hi",
        "whatsapp_phone_number": "+1-541-920-2635",
        "type": "whatsapp",
    }

    assert FlyWhatsAppDestination(
        **base, additional_metadata={"wave": "2"}
    ).additional_metadata == {"wave": "2"}
    assert FlyWhatsAppDestination(**base, additional_metadata=None) \
        .additional_metadata is None


def test_the_form_type_literals_match_what_the_union_discriminates_on():
    """The form's `type` strings are load-bearing, not cosmetic.

    Both classes use a Literal discriminator precisely because their required
    fields overlap: without it pydantic's smart union can resolve one to the
    other by ignoring an extra field. So 'whatsapp' and 'multi' in
    Destination.tsx's emptyStates must be exactly these.
    """
    from .study_conf import FlyWhatsAppDestination

    assert FlyWhatsAppDestination.model_fields["type"].annotation == Literal["whatsapp"]
    assert FlyMultiDestination.model_fields["type"].annotation == Literal["multi"]
