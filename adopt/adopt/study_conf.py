from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from math import floor
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, model_validator

Params = Dict[str, Any]
Budget = dict[str, float]


class DataSourceConf(BaseModel):
    name: str
    source: str
    credentials_key: str
    config: Any = None


class ExtractionFunctionConf(BaseModel):
    function: str
    params: Any = None


class ExtractionConf(BaseModel):
    location: str
    key: str
    name: str
    functions: list[ExtractionFunctionConf]
    value_type: str
    aggregate: str


class SourceExtractionConf(BaseModel):
    extraction_confs: list[ExtractionConf]
    user_variable: Optional[str] = None


class InferenceDataConf(BaseModel):
    data_sources: dict[str, SourceExtractionConf]


class UserInfo(BaseModel):
    survey_user: str
    token: str


# add max_budget - for max daily budget
# make budget optional - only for proportional


class TargetVar(BaseModel):
    type: str
    value: Union[str, int, float]


class QuestionTargeting(BaseModel):
    op: str
    vars: List[Union[TargetVar, QuestionTargeting]]  # type: ignore


class FlyMessengerDestination(BaseModel):
    type: str
    name: str
    initial_shortcode: str
    welcome_message: str
    button_text: str
    additional_metadata: Optional[dict[str, str]] = None


class WebDestination(BaseModel):
    type: str
    name: str
    url_template: str  # create variables, like ref, which can be used.


class AppDestination(BaseModel):
    type: str
    name: str
    facebook_app_id: str
    app_install_link: str
    deeplink_template: str
    app_install_state: str
    user_device: list[str]
    user_os: list[str]


DestinationConf = Union[FlyMessengerDestination, AppDestination, WebDestination]


class BaseRecruitmentConf(BaseModel, ABC):
    @property
    @abstractmethod
    def campaign_names(self):
        pass

    @property
    @abstractmethod
    def base_campaign_name(self) -> str:
        pass

    @property
    @abstractmethod
    def opt_budget(self):
        pass

    @property
    @abstractmethod
    def opt_sample_size(self):
        pass

    @abstractmethod
    def get_inference_window(self, now: datetime) -> Tuple[datetime, datetime]:
        pass

    @abstractmethod
    def spend_for_day(
        self,
        strata: Union[List[Stratum], List[StratumConf]],
        min_budget: float,
        budget: Optional[Budget],
        now: datetime,
    ) -> dict[str, Budget]:
        pass


def get_days_left(end_date: datetime, now: datetime):
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = end_date - now
    return delta.days


class SimpleRecruitment(BaseRecruitmentConf):
    ad_campaign_name: str
    objective: str
    optimization_goal: str
    destination_type: str
    min_budget: int
    budget: int
    max_sample: int
    start_date: datetime
    end_date: datetime
    incentive_per_respondent: float = 0

    @property
    def opt_sample_size(self):
        return self.max_sample

    @property
    def opt_budget(self):
        return self.budget

    @property
    def campaign_names(self) -> list[str]:
        return [self.ad_campaign_name]

    @property
    def base_campaign_name(self) -> str:
        return self.ad_campaign_name

    def get_inference_window(self, now: datetime) -> Tuple[datetime, datetime]:
        return self.start_date, self.end_date

    def spend_for_day(
        self,
        strata: Union[list[Stratum], list[StratumConf]],
        min_budget: float,
        budget: Optional[Budget],
        now: datetime,
    ) -> dict[str, Budget]:
        campaign = self.base_campaign_name

        if budget is None:
            return {campaign: _base_budget(min_budget, strata)}

        days_left = get_days_left(self.end_date, now)
        budget = _divide_among_days_left(budget, days_left)
        return {campaign: _deal_with_mins(min_budget, budget)}


def _pipeline_check_end_date(v):
    final_wave_start = (v["arms"] - 1) * v["offset_days"]
    days_out = final_wave_start + v["recruitment_days"]
    projected_end = v["start_date"] + timedelta(days_out)

    print(projected_end, v["end_date"])

    if projected_end != v["end_date"]:
        raise Exception(
            f"Pipeline Recruitment Config is invalid: end date {v['end_date']} "
            f"does not match other parameters which imply an end date of "
            f"{projected_end}"
        )


class PipelineRecruitmentExperiment(BaseRecruitmentConf):
    ad_campaign_name_base: str
    objective: str
    optimization_goal: str
    destination_type: str
    min_budget: int
    budget_per_arm: int
    max_sample_per_arm: int
    start_date: datetime
    end_date: datetime
    arms: int
    recruitment_days: int
    offset_days: int
    incentive_per_respondent: float = 0

    def validate_dates(self):
        # TODO: this is useless, but due to pydantic bugging out, can't
        #       use union type with root_validators. So stuck without
        #       validation for now.
        _pipeline_check_end_date(self.model_dump())

    @property
    def opt_sample_size(self):
        return self.max_sample_per_arm

    @property
    def opt_budget(self):
        return self.budget_per_arm

    @property
    def campaign_names(self) -> list[str]:
        base = self.ad_campaign_name_base
        return [f"{base}-{i+1}" for i in range(self.arms)]

    @property
    def base_campaign_name(self) -> str:
        return self.ad_campaign_name_base

    def _get_wave_markers(self, now):
        days_in = get_days_left(now, self.start_date)

        if days_in < 0:
            return None, None

        wave = floor(days_in / self.offset_days)
        wave_start = wave * self.offset_days
        wave_end = wave_start + self.recruitment_days
        return wave, wave_start, wave_end, days_in

    def get_inference_window(self, now: datetime) -> Tuple[datetime, datetime]:
        _, wave_start, wave_end, _ = self._get_wave_markers(now)
        s = self.start_date + timedelta(wave_start)
        e = self.start_date + timedelta(wave_end)
        return s, e

    def current_campaign(self, now: datetime) -> Tuple[Optional[int], Optional[int]]:
        wave, wave_start, wave_end, days_in = self._get_wave_markers(now)

        if days_in > wave_end:
            return None, None

        if wave >= self.arms:
            return None, None

        days_left = wave_end - days_in

        return wave, days_left

    def spend_for_day(
        self,
        strata: Union[list[Stratum], list[StratumConf]],
        min_budget: float,
        budget: Optional[Budget],
        now: datetime,
    ) -> dict[str, Budget]:
        # TODO: think through how to deal with re-optimization each time.
        #       right now the set up is based on running the algo again
        #       each time. Which is a bit random.

        current, days_left = self.current_campaign(now)

        if current is None:
            return {c: {s.id: 0.0 for s in strata} for c in self.campaign_names}

        current_campaign = self.campaign_names[current]

        offs = {
            c: {s.id: 0.0 for s in strata}
            for c in self.campaign_names
            if c != current_campaign
        }

        if budget is None:
            return {**offs, current_campaign: _base_budget(min_budget, strata)}

        budg = _divide_among_days_left(budget, days_left)
        budg = _deal_with_mins(min_budget, budg)

        return {**offs, current_campaign: budg}


class DestinationRecruitmentExperiment(BaseRecruitmentConf):
    ad_campaign_name_base: str
    objective: str
    optimization_goal: str
    destination_type: str
    min_budget: int
    budget_per_arm: int
    max_sample_per_arm: int
    start_date: datetime
    end_date: datetime
    destinations: list[str]
    incentive_per_respondent: float = 0

    @property
    def opt_sample_size(self):
        return self.max_sample_per_arm * len(self.destinations)

    @property
    def opt_budget(self):
        return self.budget_per_arm * len(self.destinations)

    @property
    def campaign_names(self) -> list[str]:
        base = self.ad_campaign_name_base
        return [f"{base}-{arm}" for arm in self.destinations]

    @property
    def base_campaign_name(self) -> str:
        return self.ad_campaign_name_base

    def get_inference_window(self, now: datetime) -> Tuple[datetime, datetime]:
        return self.start_date, self.end_date

    def spend_for_day(
        self,
        strata: Union[list[Stratum], list[StratumConf]],
        min_budget: float,
        budget: Optional[Budget],
        now: datetime,
    ) -> dict[str, Budget]:
        if budget is None:
            return {c: _base_budget(min_budget, strata) for c in self.campaign_names}

        arms = len(self.destinations)
        days_left = get_days_left(self.end_date, now)
        budg = _divide_among_days_left(budget, days_left)
        budg = {k: v / arms for k, v in budg.items()}
        budg = _deal_with_mins(min_budget, budg)

        return {c: budg for c in self.campaign_names}


def _base_budget(
    min_budget: float, strata: Union[list[Stratum], list[StratumConf]]
) -> Budget:
    return {s.id: min_budget for s in strata}


def _divide_among_days_left(budget: Budget, days_left) -> Budget:
    if days_left < 1:
        return {s: 0.0 for s in budget.keys()}

    budget = {k: v / days_left for k, v in budget.items()}
    return budget


def _deal_with_mins(min_budget, budget):
    # round to nearest cent!
    budget = {k: floor(v * 100) / 100 for k, v in budget.items()}
    return {k: 0 if v < min_budget else v for k, v in budget.items()}


RecruitmentConf = Union[
    SimpleRecruitment, PipelineRecruitmentExperiment, DestinationRecruitmentExperiment
]


FacebookTargeting = Dict[str, Any]

FacebookAdCreative = Dict[str, Any]


# TODO: alot of this is facebook-specific still!
class GeneralConf(BaseModel):
    name: str
    credentials_key: str
    credentials_entity: str
    ad_account: str
    opt_window: int
    # add prior parameters ?
    extra_metadata: dict[str, str] = {}  # Pydantic handles mutable default


class CreativeConf(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    destination: str
    name: str
    template: FacebookAdCreative
    template_campaign: str | None = None
    tags: list[str] | None = None


class StratumConf(BaseModel):
    id: str
    quota: float
    creatives: List[str]
    audiences: List[str]
    excluded_audiences: List[str]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting] = None

    # template -- with page / insta.
    metadata: Dict[str, str]


class Level(BaseModel):
    name: str
    template_campaign: str
    template_adset: str
    facebook_targeting: FacebookTargeting
    quota: float


class VariableConf(BaseModel):
    name: str
    properties: list[str]
    levels: list[Level]


class InvalidConfigError(BaseException):
    pass


# scenario: I want to split every N users.
# usage: set min_users only
#
# scenario: I want to split when I've BOTH past X days,
# and have at least N users.
# usage: set min_users, min_days
#
# scenario: I want to split if I've either passed X days
# or past N users
# usage: set max_users, max_days, and min_users


class Partitioning(BaseModel):
    min_users: int
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    max_users: Optional[int] = None

    @property
    def scenario(self):
        return {name for name, _ in self.__fields__.items() if getattr(self, name)}

    @model_validator(mode="before")
    @classmethod
    def validate_scenario(cls, values):
        valid_scenarios = [
            {"min_users"},
            {"min_users", "min_days"},
            {"min_users", "max_users", "max_days"},
        ]

        scenario = {k for k, v in values.items() if v is not None}

        if scenario not in valid_scenarios:
            raise InvalidConfigError(
                f"Invalid partitioning config. The following fields "
                f"were all set: {scenario}. Please see documentation for "
                f"valid combinations."
            )

        return values


def validate(values, subtype, subtype_confs):
    if subtype not in subtype_confs:
        raise InvalidConfigError(
            f"Invalid subtype: {subtype}. " f"We support: {list(subtype_confs.keys())}"
        )

    conf = subtype_confs[subtype]
    if conf:
        attr, type_ = conf
        val = values.get(attr)
        if not isinstance(val, type_):
            raise InvalidConfigError(
                f"Invalid config. Subtype {subtype} "
                f"requires a {type_} value for {attr}"
            )


class SimpleRandomizationConf(BaseModel):
    arms: int


class RandomizationConf(BaseModel):
    name: str
    strategy: str
    config: Union[SimpleRandomizationConf]

    def __post_init__(self):
        subtype_confs = {
            "SIMPLE": ("config", SimpleRandomizationConf),
        }
        validate(self, self.subtype, subtype_confs)


class LookalikeSpec(BaseModel):
    country: str
    ratio: float
    starting_ratio: float


class Lookalike(BaseModel):
    target: int
    spec: LookalikeSpec


class AudienceConf(BaseModel):
    name: str
    subtype: str
    question_targeting: Optional[QuestionTargeting] = None
    lookalike: Optional[Lookalike] = None
    partitioning: Optional[Partitioning] = None

    @model_validator(mode="before")
    @classmethod
    def __post_init__(cls, values):
        subtype_confs = {
            "CUSTOM": None,
            "LOOKALIKE": ("lookalike", Lookalike),
            "PARTITIONED": ("partitioning", Partitioning),
        }

        validate(values, values["subtype"], subtype_confs)
        return values


class Audience(BaseModel):
    name: str
    page_ids: list[str]
    users: list[str]


class LookalikeAudience(BaseModel):
    name: str
    spec: LookalikeSpec
    origin_audience: Audience


AnyAudience = Union[Audience, LookalikeAudience]


class Stratum(BaseModel):
    id: str
    quota: float
    creatives: List[CreativeConf]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting] = None
    metadata: dict[str, str]


# TODO: add some good integration tests where you build on test_studies
#       and test the instructions at different points in time.
#       need a nice helper for creating facebook campaign state at any
#       point.


class StudyConf(BaseModel):
    id: str
    user: UserInfo
    general: GeneralConf
    destinations: list[DestinationConf]
    audiences: list[AudienceConf]
    creatives: list[CreativeConf]
    strata: list[StratumConf]
    recruitment: RecruitmentConf

    # WAIT - not optional?
    inference_data: Optional[InferenceDataConf] = None
    data_sources: Optional[list[DataSourceConf]] = None

    @property
    def campaign_names(self) -> list[str]:
        return self.recruitment.campaign_names

    @property
    def base_campaign_name(self) -> str:
        return self.recruitment.base_campaign_name
