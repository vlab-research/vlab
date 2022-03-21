from datetime import datetime

from .study_conf import (DestinationRecruitmentExperiment,
                         PipelineRecruitmentExperiment, SimpleRecruitment)
import pytest

def _dt(day, month=1, year=2022):
    return datetime(year, month, day)


def _simple(name="foo", start_date=_dt(1), end_date=_dt(3)):
    return SimpleRecruitment(
        ad_campaign_name=name,
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
):
    return PipelineRecruitmentExperiment(
        ad_campaign_name_base=name,
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
):
    return DestinationRecruitmentExperiment(
        ad_campaign_name_base=name,
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


def _dt(day, month=1, year=2022):
    return datetime(year=year, month=month, day=day)


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


def test_simple_spend_for_day_returns_budget_proposal_spread_over_days_and_floored():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]

    start = _dt(1)
    end = _dt(10)
    now = _dt(8)
    r = _simple("study", start, end)

    budget = {"foo": 2.2, "bar": 2.0, "baz": 3.5}  # quite a bit under budget!
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {"study": {"foo": 1.0, "bar": 1.0, "baz": 1.0}}


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
    budget = {"foo": 4.3, "bar": 8.0, "baz": 13.5}

    res = r.spend_for_day(strata, 1, budget, now)

    assert res == {
        "study-baz": {"foo": 2.0, "bar": 4.0, "baz": 6.0},
        "study-qux": {"foo": 2.0, "bar": 4.0, "baz": 6.0},
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
        "study-baz": {"foo": 1.0, "bar": 2.0, "baz": 3.0},
        "study-qux": {"foo": 1.0, "bar": 2.0, "baz": 3.0},
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
        name="foo", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=4
    )
    assert r.current_campaign(now) == (None, None)


def test_pipeline_pick_active_campaign_picks_next_campaign_when_it_starts():
    start = _dt(1)
    now = _dt(5)
    end = _dt(7)

    r = _pipeline(
        name="foo", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=4
    )
    assert r.current_campaign(now) == (1, 2)


def test_pipeline_pick_active_campaign_stops_when_finished():
    start = _dt(1)
    now = _dt(9)
    end = _dt(7)

    r = _pipeline(
        name="foo", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=4
    )
    assert r.current_campaign(now) == (None, None)


def test_pipeline_pick_active_campaign_keeps_going_recruitment_days_and_offset_same():
    start = _dt(1)
    now = _dt(3)
    end = _dt(5)

    r = _pipeline(
        name="foo", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=2
    )
    assert r.current_campaign(now) == (1, 2)


def test_pipeline_spend_for_day_sets_budget_to_zero_if_no_more_days():
    strata = [_strat("foo"), _strat("bar"), _strat("baz")]
    start = _dt(1)
    now = _dt(10)
    end = _dt(7)

    r = _pipeline(
        name="study", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=4
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
        name="study", start_date=start, end_date=end, arms=2, recruitment_days=2, offset_days=4
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
        name="study", start_date=start, end_date=end, arms=2, recruitment_days=3, offset_days=6
    )

    budget = {"foo": 9.0, "bar": 12.0, "baz": 13.7}
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 3.0, "bar": 4.0, "baz": 4.0},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }

    budget = {"foo": 6.0, "bar": 8.0, "baz": 9.7}
    now = _dt(2)
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 3.0, "bar": 4.0, "baz": 4.0},
        "study-2": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
    }

    now = _dt(8)
    res = r.spend_for_day(strata, 1, budget, now)
    assert res == {
        "study-1": {"foo": 0.0, "bar": 0.0, "baz": 0.0},
        "study-2": {"foo": 3.0, "bar": 4.0, "baz": 4.0},
    }


def test_pipeline_spend_can_check_validity_of_end_date():
    start = _dt(1)
    end = _dt(10)

    r = _pipeline(
        name="study", start_date=start, end_date=end, arms=2, recruitment_days=3, offset_days=6
    )

    r.validate_dates()

    start = _dt(1)
    r = _pipeline(
        name="study", start_date=start, end_date=end, arms=3, recruitment_days=3, offset_days=3
    )

    r.validate_dates()

    with pytest.raises(Exception):
        r = _pipeline(
            name="study", start_date=start, end_date=end, arms=3, recruitment_days=3, offset_days=5
        )
        r.validate_dates()
