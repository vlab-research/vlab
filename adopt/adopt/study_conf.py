from __future__ import annotations

# from dataclasses import dataclass, fields
from dataclasses import fields
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional, Union

from pydantic import BaseModel, ValidationError, root_validator
from pydantic.dataclasses import dataclass
from toolz import groupby

Params = Dict[str, Any]


class SourceConf(BaseModel):
    name: str
    source: str
    config: Any


class ExtractionConf(BaseModel):
    key: str
    name: str
    function: str
    params: Any
    value_type: str
    aggregate: str


class InferenceDataSource(BaseModel):
    variable_extraction: list[ExtractionConf]
    metadata_extraction: list[ExtractionConf]


class InferenceDataConf(BaseModel):
    data_sources: dict[str, InferenceDataSource]


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
    name: str
    initial_shortcode: str


class WebDestination(BaseModel):
    name: str
    url_template: str  # create variables, like ref, which can be used.


class AppDestination(BaseModel):
    name: str
    facebook_app_id: str
    app_install_link: str
    deeplink_template: str
    app_install_state: str
    user_device: list[str]
    user_os: list[str]


DestinationConf = Union[FlyMessengerDestination, AppDestination, WebDestination]


class PipelineRecruitmentExperiment(BaseModel):
    arms: int
    recruitment_days: int
    offset_days: int


class DestinationRecruitmentExperiment(BaseModel):
    arms: int
    creative_mapping: dict[int, list[str]]


RecruitmentExperimentConf = Union[
    PipelineRecruitmentExperiment, DestinationRecruitmentExperiment
]

FacebookTargeting = Dict[str, Any]


class CampaignConf(BaseModel):
    optimization_goal: str
    destination_type: str
    page_id: str
    instagram_id: Optional[str]
    budget: float
    min_budget: float
    opt_window: int
    start_date: datetime
    end_date: datetime
    proportional: bool
    ad_account: str
    ad_campaign_name: str
    country_code: str
    extra_metadata: dict[str, str]


class CreativeConf(BaseModel):
    destination: str
    name: str
    image_hash: str
    body: str
    link_text: str
    welcome_message: Optional[str] = None  # messenger only
    button_text: Optional[str] = None  # messenger only
    tags: Optional[list[str]] = None


class StratumConf(BaseModel):
    id: str
    quota: Union[int, float]
    creatives: List[str]
    audiences: List[str]
    excluded_audiences: List[str]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: Dict[str, str]


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

    @root_validator(pre=False)
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

    @root_validator(pre=False)
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
    pageid: str
    users: List[str]


class LookalikeAudience(BaseModel):
    name: str
    spec: LookalikeSpec
    origin_audience: Audience


AnyAudience = Union[Audience, LookalikeAudience]


class Stratum(BaseModel):
    id: str
    quota: Union[int, float]
    creatives: List[CreativeConf]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: dict[str, str]


# TODO:
# more than just names
# you also want... days, creatives, etc.
# think about what you need

# also add some good integration tests where you build on test_studies
# and test the instructions at different points in time.
# need a nice helper for creating facebook campaign state at any
# point.


def get_campaign_names(
    base: str, recruitment_experiment: Optional[RecruitmentExperimentConf]
) -> list[str]:

    if recruitment_experiment is None:
        return [base]

    arms = recruitment_experiment.arms
    arm_names = [i + 1 for i in range(arms)]
    return [f"{base}-{arm}" for arm in arm_names]


class StudyConf(BaseModel):
    id: str
    user: UserInfo
    general: CampaignConf
    destinations: list[DestinationConf]
    audiences: list[AudienceConf]
    creatives: list[CreativeConf]
    strata: list[StratumConf]

    recruitment_experiment: Optional[RecruitmentExperimentConf] = None
    # WAIT - not optional?
    inference_data: Optional[InferenceDataConf] = None
    data_sources: Optional[list[SourceConf]] = None

    @property
    def campaign_names(self) -> list[str]:
        return get_campaign_names(
            self.general.ad_campaign_name, self.recruitment_experiment
        )
