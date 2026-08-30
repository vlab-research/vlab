from datetime import datetime, timedelta
from typing import Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from .study_conf import (
    CreativeConf,
    DestinationConf,
    DestinationRecruitmentExperiment,
    destination_type_for,
    ExtractionConf,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    GeneralConf,
    InferenceDataConf,
    InvalidConfigError,
    MULTI_DESTINATION_TYPE,
    PipelineRecruitmentExperiment,
    QuestionTargeting,
    SimpleRecruitment,
    SourceExtractionConf,
    StratumConf,
    StudyConf,
    TargetVar,
    UserInfo,
    WebDestination,
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
    min_budget=1,
):
    return SimpleRecruitment(
        ad_campaign_name=name,
        objective=objective,
        optimization_goal=optimization_goal,
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
    min_budget=1,
):
    return PipelineRecruitmentExperiment(
        ad_campaign_name_base=name,
        objective=objective,
        optimization_goal=optimization_goal,
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
    min_budget=1,
):
    return DestinationRecruitmentExperiment(
        ad_campaign_name_base=name,
        objective=objective,
        optimization_goal=optimization_goal,
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


def _whatsapp_destination(shortcode="mnchweek", ref_mode=None):
    return FlyWhatsAppDestination(
        type="whatsapp",
        name="whatsapp",
        initial_shortcode=shortcode,
        welcome_message="Tap send to start",
        whatsapp_phone_number="+1-541-920-2635",
        ref_mode=ref_mode,
    )


def _whatsapp_study(metadata, ref_mode=None, destination_name="whatsapp"):
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
        destinations=[_whatsapp_destination(ref_mode=ref_mode)],
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
        recruitment=_simple(),
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
    study = _whatsapp_study({"State": "Bauchi State"})
    assert study.strata[0].metadata["State"] == "Bauchi State"


def test_full_ref_with_a_genuinely_undeliverable_value_is_still_rejected():
    with pytest.raises(InvalidConfigError, match="North/South"):
        _whatsapp_study({"Region": "North/South"})


def test_full_ref_with_safe_stratum_metadata_is_accepted():
    study = _whatsapp_study({"gender": "women", "creative": "3B"})
    assert study.strata[0].metadata["gender"] == "women"


def test_an_encoded_ref_tolerates_metadata_it_never_ships():
    """The check fires only on the mode that puts values in the autofill text.

    A stratum whose values fly's entry pattern cannot parse is fine in ref_mode
    "encoded", because none of them travel there — the ad table carries the
    stratum instead.
    """
    study = _whatsapp_study({"Region": "North/South"}, ref_mode="encoded")
    assert study.strata[0].metadata["Region"] == "North/South"


def test_full_ref_ignores_strata_that_do_not_publish_through_that_destination():
    # A stratum whose creatives all point elsewhere never produces a WhatsApp
    # ref, so its metadata cannot break one.
    study = _whatsapp_study(
        {"State": "Bauchi State"}, destination_name="somewhere-else"
    )
    assert study.strata[0].metadata["State"] == "Bauchi State"


def test_full_ref_validation_covers_the_form_key_and_extra_metadata():
    # `form` is folded in from the shortcode, which is already validated, but
    # extra_metadata is not -- and it rides in the ref too.
    study = _whatsapp_study({"gender": "women"})
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


def test_a_stored_destination_type_on_the_recruitment_conf_is_ignored():
    """The field is gone from the model; ~940 stored confs still carry it.

    Removing it had to be free for every study already in production, and it is:
    pydantic v2 ignores unknown keys by default, so a conf written when the field
    existed loads unchanged and simply drops it. Nothing reads it any more --
    `adset_destination_type` derives the ad set's value from the destinations.
    """
    study = _whatsapp_study({"gender": "women"}).model_dump()
    study["recruitment"]["destination_type"] = "MESSENGER"

    conf = StudyConf(**study)

    assert not hasattr(conf.recruitment, "destination_type")


def test_every_destination_names_its_own_meta_enum_value():
    """`destination_type_for` is total, which is what let the field go.

    The values are Meta's ad-set enum, not fly's destination kinds. That
    distinction is the whole bug this replaced: the dashboard fed fly's kinds
    (`multi`, `web`) uppercased into a field wanting Meta's enum, and production
    ended up holding `MULTI` and `WEB` -- neither of which Meta defines.
    """
    assert destination_type_for(_whatsapp_destination()) == "WHATSAPP"
    assert (
        destination_type_for(
            FlyMessengerDestination(
                type="messenger",
                name="messenger",
                initial_shortcode="mnchweek",
                welcome_message="hi",
                button_text="Start",
            )
        )
        == "MESSENGER"
    )
    assert (
        destination_type_for(
            FlyMultiDestination(
                type="multi",
                name="multi",
                initial_shortcode="mnchweek",
                welcome_message="hi",
                button_text="Start",
                whatsapp_phone_number="+1-541-920-2635",
            )
        )
        == "MESSAGING_MESSENGER_WHATSAPP"
    )


def test_the_multi_destination_type_is_metas_token_not_the_word_multi():
    """Regression: production held `destination_type: MULTI` on a live study.

    `MULTI` is fly's name for the destination kind. Meta's ad-set enum value is
    `MESSAGING_MESSENGER_WHATSAPP`, and `marketing.py` sends whatever it is given
    verbatim. Worse than a rejected ad set, the bad value defeated the check that
    existed to catch it -- `MULTI` matched no recognised set, so the validator
    returned early and validated nothing.
    """
    assert MULTI_DESTINATION_TYPE == "MESSAGING_MESSENGER_WHATSAPP"
    assert MULTI_DESTINATION_TYPE != "MULTI"


# ---------------------------------------------------------------------------
# Thinning the ref without reading the mapping.
#
# A ref that carries a token instead of the stratum only works if the study also
# reads the ad -> stratum mapping. One without the other leaves the study with
# no attribution at all -- the ref no longer carries the stratum and nothing
# looks the ad up.
# ---------------------------------------------------------------------------


def _messenger_study(ref_mode=None, inference_data=None):
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
                ref_mode=ref_mode,
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
    assert thins_its_ref_without_reading_the_mapping(_messenger_study()) == []


def test_thinning_the_ref_with_no_ad_confs_is_flagged():
    study = _messenger_study("encoded", _inference_conf("md:gender"))
    assert thins_its_ref_without_reading_the_mapping(study) == ["messenger"]


def test_thinning_the_ref_with_a_lookup_conf_is_fine():
    conf = InferenceDataConf(
        data_sources={"fly": SourceExtractionConf(extraction_confs=[_lookup_conf("gender")])}
    )
    assert (
        thins_its_ref_without_reading_the_mapping(_messenger_study("encoded", conf))
        == []
    )


# ---------------------------------------------------------------------------
# The mapping field itself.


def test_mapping_defaults_to_raw():
    # The default is the historical behaviour, which is what lets every conf
    # written before this field existed keep meaning what it meant.
    assert _extraction_conf("md:gender").mapping == "raw"
    assert _extraction_conf("md:gender").is_ad_table_lookup is False


def test_a_lookup_reads_its_token_from_either_location():
    # Location says where to read and mapping says what the value means, and
    # neither constrains the other. A respondent recruited by a web or app
    # destination lands on the researcher's own page, so their token comes back
    # as a survey field rather than as metadata fly stamped.
    conf = _extraction_conf("gender", location="variable", mapping="ad_table_lookup")

    assert conf.is_ad_table_lookup is True


def test_an_unknown_mapping_is_rejected():
    with pytest.raises(ValidationError):
        _extraction_conf("md:gender", mapping="ad_id_lookup")


def test_thinning_the_ref_with_no_inference_conf_at_all_is_flagged():
    assert thins_its_ref_without_reading_the_mapping(
        _messenger_study("encoded", None)
    ) == ["messenger"]


def test_a_thinned_web_destination_is_flagged_the_same_way():
    # No type check at all: a web destination whose ref stops carrying the
    # stratum has exactly the problem a Messenger one does.
    study = _messenger_study()
    study_dict = study.model_dump()
    study_dict["destinations"] = [
        {
            "type": "web",
            "name": "web",
            "url_template": "https://survey.example/?r={ref}",
            "ref_mode": "encoded",
        }
    ]
    study_dict["creatives"][0]["destination"] = "web"

    assert thins_its_ref_without_reading_the_mapping(StudyConf(**study_dict)) == ["web"]


def test_a_thinned_whatsapp_destination_is_flagged_the_same_way():
    # Every destination type is asked, with no type check: what a ref carries is
    # a property of the ref, not of the channel carrying it.
    study = _whatsapp_study({"gender": "women"}, ref_mode="encoded")
    assert thins_its_ref_without_reading_the_mapping(study) == ["whatsapp"]


# ---------------------------------------------------------------------------
# The destination union is discriminated on `type`.
#
# It was a plain Union until 2026-08-30, resolved by shape. Every test below is
# a case that passed silently then, producing the wrong class.
# ---------------------------------------------------------------------------


def _dest(**over):
    base = {
        "type": "multi",
        "name": "Fly Multi",
        "initial_shortcode": "vlpulseng",
        "welcome_message": "Take our 5-minute survey",
        "button_text": "Start Survey!",
        "whatsapp_phone_number": "+1-541-920-2635",
        "ref_mode": "encoded",
    }
    return {**base, **over}


def _parse_destination(d):
    return TypeAdapter(DestinationConf).validate_python(d)


def test_a_multi_destination_actually_parses_as_multi():
    """The regression. This is the entire bug, in one assertion.

    `FlyMessengerDestination` came first in the union and declared `type: str`,
    so it accepted any discriminator value -- and a multi conf carries every
    field Messenger requires, with `whatsapp_phone_number` merely ignored as an
    extra. So this returned FlyMessengerDestination and FlyMultiDestination was
    unreachable: `type: "multi"` never once produced one.
    """
    assert isinstance(_parse_destination(_dest()), FlyMultiDestination)


def test_the_downgrade_produced_a_messenger_adset_for_a_multi_study():
    """Why it mattered, rather than merely being untidy.

    Measured on `vl-pulse-nigeria-smoke`, 2026-08-30. The downgraded
    destination derived MESSENGER, so adopt built a MESSENGER ad set and
    injected no multi asset_feed_spec. The template ad's own WhatsApp
    call-to-action passed through, and Meta refused the ad -- "Inconsistent
    Campaign Destination Type With App Destination", subcode 2490279.

    That rejection was luck. With a Messenger-only template the same conf
    builds a Messenger-only ad for a study configured as multi, silently.
    """
    assert destination_type_for(_parse_destination(_dest())) == (
        MULTI_DESTINATION_TYPE
    )


def test_a_multi_destination_without_a_phone_number_is_refused_by_name():
    """It used to be *accepted*, as a Messenger destination.

    This is the exact conf `vl-pulse-nigeria-smoke` held: the field was absent,
    so the multi member could not match, so the shape-matched union fell to
    Messenger and threw the missing field away. The error must now name the
    field, because that is the only way an operator learns what to fill in.
    """
    with pytest.raises(ValidationError, match="whatsapp_phone_number"):
        _parse_destination({k: v for k, v in _dest().items()
                            if k != "whatsapp_phone_number"})


def test_an_unknown_destination_type_is_refused_rather_than_becoming_messenger():
    """`type: "total-nonsense"` used to validate, as a Messenger destination."""
    with pytest.raises(ValidationError, match="does not match any of the expected"):
        _parse_destination(_dest(type="total-nonsense"))


def test_whatsapp_no_longer_depends_on_an_accident_to_parse():
    """It parsed correctly before, but only by luck.

    `FlyWhatsAppDestination` has no `button_text`, so a whatsapp conf failed
    Messenger's required field and fell through to the right member. Add
    `button_text` to Messenger's optional set, or to WhatsApp's shape, and
    WhatsApp would have started silently downgrading too.
    """
    d = _parse_destination({
        "type": "whatsapp",
        "name": "Fly WhatsApp",
        "initial_shortcode": "vlpulseng",
        "welcome_message": "Tap send",
        "whatsapp_phone_number": "+1-541-920-2635",
        "button_text": "Start Survey!",
    })
    assert isinstance(d, FlyWhatsAppDestination)


def test_a_conf_with_no_type_at_all_still_loads_as_messenger():
    """45 stored confs across 11 studies predate the `type` field.

    They resolved to Messenger under the old union because it was first. The
    discriminator would reject them outright ("Unable to extract tag"), so the
    value they already behave as is filled in before the tag is read. This is
    what makes the change free for every study in production.
    """
    d = _parse_destination({
        "name": "Fly",
        "initial_shortcode": "vlpulseng",
        "welcome_message": "hi",
        "button_text": "Start",
    })
    assert isinstance(d, FlyMessengerDestination)


def test_both_stored_spellings_of_the_web_type_name_the_same_class():
    """`web` on 4 studies, `website` on 2, measured 2026-08-30. Both are kept
    as discriminator values rather than rewriting stored JSON."""
    for spelling in ["web", "website"]:
        d = _parse_destination({
            "type": spelling, "name": "w",
            "url_template": "https://survey.example/?r={ref}",
        })
        assert isinstance(d, WebDestination)


# ---------------------------------------------------------------------------
# destination_type is derived from the destinations, and multi-destination.
#
# There was a validator here that refused a recruitment `destination_type` no
# destination backed -- the misroute it caught being an ad whose Messenger arm
# routes while its WhatsApp arm quietly recruits into FALLBACK_FORM. The field
# is gone, so that state is now unrepresentable rather than rejected, and these
# tests assert the derivation instead. `adset_destination_type` in
# test_marketing.py covers the one error left: creatives in a single stratum
# asking for different channels.
# ---------------------------------------------------------------------------


def _messenger_only_study():
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
        recruitment=_simple(),
    )


def test_a_messenger_only_study_derives_messenger():
    """The ~940 production studies. Untouched by the removal.

    They all carry a stored `destination_type` of MESSENGER and Messenger
    destinations that derive MESSENGER anyway, so the ad set Meta receives is
    byte-identical either way. That equivalence is what made the field safe to
    delete rather than migrate.
    """
    study = _messenger_only_study()
    assert [destination_type_for(d) for d in study.destinations] == ["MESSENGER"]


def test_the_misroute_the_old_validator_caught_is_now_unrepresentable():
    """MESSAGING_MESSENGER_WHATSAPP over Messenger-only destinations.

    This used to build happily: the ads run multi-destination, the Messenger arm
    keeps its quick-reply welcome message and routes fine, and the WhatsApp arm
    has no autofill token at all, so every WhatsApp clicker Meta routes there
    lands on FALLBACK_FORM -- a real survey belonging to a real researcher. Half
    the ad works, which is why the operator has no reason to suspect it; fly's
    onboarding doc calls it "the single easiest way to misconfigure a WhatsApp
    ad".

    There is no longer a way to say it. A study's channel is whatever its
    destinations open, and a Messenger destination cannot open WhatsApp.
    """
    study = _messenger_only_study()

    assert not hasattr(study.recruitment, "destination_type")
    assert MULTI_DESTINATION_TYPE not in [
        destination_type_for(d) for d in study.destinations
    ]


def _multi_study(optimization_goal="CONVERSATIONS", ref_mode=None):
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
                ref_mode=ref_mode,
            )
        ],
        audiences=[],
        creatives=[CreativeConf(destination="multi", name="Smiling", template={})],
        strata=[],
        recruitment=_simple(optimization_goal=optimization_goal),
    )


def test_a_multi_destination_derives_metas_combination_token():
    """Not the word `multi`, which is fly's name for the destination kind.

    Production held `destination_type: MULTI` on a study configured the evening
    of 2026-08-27: the dashboard fed its destination-kind list, uppercased, into
    a field wanting Meta's ad-set enum. `marketing.py` sends the value verbatim,
    so Meta would have rejected the ad set -- and the check that should have
    caught it was itself defeated, because `MULTI` matched no recognised set and
    the validator returned early.
    """
    study = _multi_study()
    assert [destination_type_for(d) for d in study.destinations] == [
        "MESSAGING_MESSENGER_WHATSAPP"
    ]


def test_multi_destination_accepts_link_clicks():
    """The CONVERSATIONS requirement is gone, and this is why.

    Meta's click-to-multidestination guide says optimization_goal "Must be set
    to CONVERSATIONS", and a validator here enforced that. The guide is wrong:
    `MESSAGING_MESSENGER_WHATSAPP` + `LINK_CLICKS` was measured being ACCEPTED
    on a live ad set (planning/click-to-whatsapp-ads.md §6a).

    Enforcing it was not merely redundant. A Page subject to European privacy
    rules cannot use CONVERSATIONS for click-to-WhatsApp at all, so requiring
    CONVERSATIONS made multi-destination unbuildable on such a Page -- which is
    the Page `vl-pulse-nigeria-smoke` runs on.
    """
    assert (
        _multi_study(optimization_goal="LINK_CLICKS").recruitment.optimization_goal
        == "LINK_CLICKS"
    )
    assert (
        _multi_study(optimization_goal="CONVERSATIONS").recruitment.optimization_goal
        == "CONVERSATIONS"
    )


def test_meta_is_left_to_judge_the_goal_it_actually_accepts():
    """No guessing on Meta's behalf from a doc it contradicts.

    An unusual pairing is not refused here. Meta rejects at ad set create with
    an error naming the fields, and that rejection is authoritative in a way
    this repo's reading of the guide was not.
    """
    assert (
        _multi_study(optimization_goal="IMPRESSIONS").recruitment.optimization_goal
        == "IMPRESSIONS"
    )


def test_single_destination_whatsapp_still_accepts_link_clicks():
    """Unchanged, and it was never constrained. Kept because a Page subject to
    European privacy rules cannot use CONVERSATIONS for click-to-WhatsApp at
    all, so this is the pairing such a Page depends on."""
    study = _whatsapp_study({"gender": "women"}).model_dump()
    study["recruitment"]["optimization_goal"] = "LINK_CLICKS"

    assert StudyConf(**study).recruitment.optimization_goal == "LINK_CLICKS"


def test_a_multi_destination_shortcode_keeps_the_narrow_alphabet():
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


def test_a_multi_destination_number_must_be_dialable():
    with pytest.raises(InvalidConfigError, match="dialable"):
        FlyMultiDestination(
            type="multi",
            name="multi",
            initial_shortcode="mnchweek",
            welcome_message="Hi",
            button_text="Start",
            whatsapp_phone_number="10925130295730592",
        )


def test_a_multi_destination_exposes_the_number_in_metas_shape():
    dest = FlyMultiDestination(
        type="multi",
        name="multi",
        initial_shortcode="mnchweek",
        welcome_message="Hi",
        button_text="Start",
        whatsapp_phone_number="+1-541-920-2635",
    )
    assert dest.promoted_phone_number == "15419202635"


def test_a_thin_multi_ref_without_an_ad_conf_is_reported():
    """A multi destination in ref_mode "encoded" has the ad -> stratum mapping
    as its only attribution. Reported for the same reason as the others."""
    study = _multi_study(ref_mode="encoded")
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
    # Not sent by a form that predates the field, and must therefore have a
    # default: the mode it already runs under.
    assert dest.resolved_ref_mode == "metadata"
    assert dest.additional_metadata is None


def test_the_dashboard_multi_form_shape_parses():
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
    assert dest.resolved_ref_mode == "metadata"


def test_the_dashboard_additional_metadata_shape_parses():
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
