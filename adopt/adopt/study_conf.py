from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from math import floor
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

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

    # Whether the ad's ref carries the full stratum metadata or only the
    # shortcode. Named to match FlyWhatsAppDestination's field: it is one
    # concept, and the two channels differ only in their default.
    #
    # Defaults True, the historical behaviour, because every existing study
    # depends on it — and because turning it off changes the *creative*, which
    # makes reconciliation rewrite that study's ads on its next run.
    #
    # Turning it off is the point of the whole ad-id design. It stops vlab
    # shipping its stratum vocabulary into fly inside every message and leaves
    # the ref doing only the job it cannot delegate: routing. Attribution then
    # comes from the frozen ad_attributions row instead, so this is only safe
    # for a study whose inference_data conf reads `location: "ad"`.
    #
    # This flag must never reach creative_metadata — see create_creative.
    include_metadata_in_ref: bool = True


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


# Click-to-WhatsApp entry tokens live under a much narrower grammar than the
# Messenger ref does, and the difference is load-bearing.
#
# A CTWA referral carries no advertiser-settable `ref` — url_tags was measured
# not to reach WhatsApp at all — so fly recovers the shortcode from the ad's
# autofill message text, which the respondent's first message prefills. fly
# matches that text against an anchored, full-match pattern (WHATSAPP_ENTRY_REF
# in replybot/lib/event-normalizer.js):
#
#     /^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$/i
#
# Two consequences, both verified against that regex:
#
# 1. The token must lead with `form.`. `make_ref` leads with `creative.`, so its
#    output can never match, whatever the values are. A WhatsApp ref has to be
#    serialised form-first.
# 2. Every token is `[A-Za-z0-9_-]+`. No spaces, no `%`. `quote()` turns a space
#    into `%20`, and `%` is not in the class either, so a value like
#    "Bauchi State" fails encoded *and* raw.
#
# A failure here is silent and expensive: Meta delivers the text intact (dots
# and spaces both survive `autofill_message.content`, measured), fly's pattern
# rejects it, no conversation_started is derived, and the arrival falls through
# to FALLBACK_FORM — a real survey, so the respondents look like completions
# rather than errors. That is the VIR-19 failure shape. Hence: validate at
# config time, never emit and hope.
WHATSAPP_REF_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def whatsapp_ref_token_safe(value: str) -> bool:
    """True if `value` can survive fly's WhatsApp entry pattern as one token."""
    return bool(WHATSAPP_REF_TOKEN.match(value))


def unsafe_whatsapp_ref_tokens(values: Dict[str, str]) -> List[str]:
    """The `key=value` pairs that would break a WhatsApp ref, for error text.

    Keys are checked as well as values: both become dot-separated tokens.
    """
    bad = []
    for k, v in values.items():
        if not whatsapp_ref_token_safe(k) or not whatsapp_ref_token_safe(str(v)):
            bad.append(f"{k}={v}")
    return sorted(bad)


# Ad set destination_types that include WhatsApp, from Meta's destination_type
# table (planning/click-to-whatsapp-ads.md). A CTWA destination has to run in
# one of these or its promoted_object means nothing and the ad never reaches
# WhatsApp.
WHATSAPP_DESTINATION_TYPES = {
    "WHATSAPP",
    "MESSAGING_MESSENGER_WHATSAPP",
    "MESSAGING_INSTAGRAM_DIRECT_WHATSAPP",
    "MESSAGING_INSTAGRAM_DIRECT_MESSENGER_WHATSAPP",
}


def normalize_whatsapp_phone_number(value: str) -> str:
    """Digits only — what promoted_object.whatsapp_phone_number expects.

    Measured rather than inferred: adopt/scripts/ctwa_probe.py records that the
    promoted-object reference types this as a *numeric string*, while
    credentials store the display form ("+1-541-920-2635"), and strips to
    digits before sending. There is no existing phone normaliser in this repo
    to reuse — this is the first thing in vlab that sends a phone number to
    Meta.
    """
    return "".join(ch for ch in value if ch.isdigit())


def whatsapp_phone_number_valid(value: str) -> bool:
    """E.164 permits at most 15 digits, and no dialable number has under 7."""
    return 7 <= len(normalize_whatsapp_phone_number(value)) <= 15


class FlyWhatsAppDestination(BaseModel):
    """A click-to-WhatsApp destination.

    Shaped after FlyMessengerDestination, minus `button_text` (WhatsApp has no
    quick-reply button; the respondent gets a prefilled compose box) and plus
    `include_metadata_in_ref`.

    `type` is a Literal, unlike its siblings, because this model's required
    fields are a strict subset of FlyMessengerDestination's — without a
    discriminator, pydantic's smart union could resolve a Messenger destination
    to this class by ignoring the extra `button_text`.
    """

    type: Literal["whatsapp"]
    name: str
    initial_shortcode: str
    # Shown above the compose box on the welcome screen; not part of the ref.
    welcome_message: str

    # The number this ad's clicks land on, as promoted_object.
    # whatsapp_phone_number. Required rather than optional even though Meta
    # treats it as optional: many numbers to one Page is documented and
    # supported, so omitting it falls back to the Page's "primary" number —
    # and an org running several would silently recruit into whichever one
    # that happens to be. Naming it is the only way to know.
    whatsapp_phone_number: str

    additional_metadata: Optional[dict[str, str]] = None

    # Opt-in: put the full stratum metadata in the autofill text, not just the
    # shortcode. Off by default, and rarely usable — see the module comment and
    # StudyConf.check_whatsapp_refs_are_deliverable. The autofill text is
    # visible to and editable by the respondent, and the ad-ID join (A5-A7)
    # already carries stratum identity to the optimizer without it, so the only
    # reason to turn this on is fly survey logic that branches on ad metadata.
    include_metadata_in_ref: bool = False

    @property
    def promoted_phone_number(self) -> str:
        """The number in the form Meta's promoted_object wants."""
        return normalize_whatsapp_phone_number(self.whatsapp_phone_number)

    @model_validator(mode="after")
    def phone_number_must_be_dialable(self):
        # At config time, not when Meta rejects the ad set. A study that cannot
        # produce a working ad should say so while someone is still looking at
        # it.
        if not whatsapp_phone_number_valid(self.whatsapp_phone_number):
            raise InvalidConfigError(
                f"WhatsApp destination '{self.name}': whatsapp_phone_number "
                f"'{self.whatsapp_phone_number}' is not a dialable number. "
                "Meta wants the number itself (any punctuation is fine, it is "
                "stripped), not the phone_number_id — sending the id is an "
                "easy way to spend a day testing the wrong number."
            )
        return self

    @model_validator(mode="after")
    def shortcode_must_survive_the_entry_pattern(self):
        # Applies in both modes: even a shortcode-only token is `form.<sc>`, so
        # an unsafe shortcode breaks the plain case too.
        if not whatsapp_ref_token_safe(self.initial_shortcode):
            raise InvalidConfigError(
                f"WhatsApp destination '{self.name}': initial_shortcode "
                f"'{self.initial_shortcode}' contains characters that fly's "
                "WhatsApp entry pattern rejects. Only letters, digits, "
                "underscore and hyphen survive; anything else means the ad "
                "recruits people into the fallback survey instead of yours."
            )
        return self


DestinationConf = Union[
    FlyMessengerDestination, AppDestination, WebDestination, FlyWhatsAppDestination
]


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
    efficiency_weight: float = 1.0  # 1.0 = variance focus, 0.0 = cost focus
    optimizer_version: Literal["closed_form", "lbfgs"] = "closed_form"

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
    efficiency_weight: float = 1.0  # 1.0 = variance focus, 0.0 = cost focus
    optimizer_version: Literal["closed_form", "lbfgs"] = "closed_form"

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
    efficiency_weight: float = 1.0  # 1.0 = variance focus, 0.0 = cost focus
    optimizer_version: Literal["closed_form", "lbfgs"] = "closed_form"

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

    @model_validator(mode="after")
    def check_whatsapp_destination_type(self):
        """A WhatsApp destination needs an ad set that actually goes to WhatsApp.

        `destination_type` is a study-wide recruitment setting, so it is
        possible to configure a WhatsApp destination on an ad set that Meta
        will route to Messenger. Nothing downstream notices: the creative is
        valid, the promoted_object is set, and the ad simply does not do what
        the study thinks it does.

        Deliberately a check rather than an override. `destination_type` is
        user-set for every existing study, and deriving it here would change
        what those studies send.
        """
        if not any(isinstance(d, FlyWhatsAppDestination) for d in self.destinations):
            return self

        destination_type = self.recruitment.destination_type
        if destination_type not in WHATSAPP_DESTINATION_TYPES:
            raise InvalidConfigError(
                f"This study has a WhatsApp destination but its recruitment "
                f"destination_type is '{destination_type}'. Meta routes the ad "
                f"set by destination_type, so the ads would not reach WhatsApp "
                f"at all. Use one of: {sorted(WHATSAPP_DESTINATION_TYPES)}."
            )

        return self

    @model_validator(mode="after")
    def check_whatsapp_refs_are_deliverable(self):
        """Reject a full-metadata WhatsApp ref that fly could never parse.

        Only fires for a WhatsApp destination with include_metadata_in_ref on,
        so every other study — and every WhatsApp study on the default
        shortcode-only setting — is untouched.

        This is the earliest point at which the check is possible: the ref's
        content comes from the strata and its deliverability from the
        destination, and those are two separate confs, POSTed independently. So
        a per-conf validator cannot see both. StudyConf is where they first
        meet, and it is assembled at the start of every reconciliation run,
        which is still before any ad exists. Failing here fails closed: the
        study creates no ads at all, rather than creating ads that recruit
        people into the fallback survey.
        """
        full_ref_destinations = [
            d
            for d in self.destinations
            if isinstance(d, FlyWhatsAppDestination) and d.include_metadata_in_ref
        ]

        if not full_ref_destinations:
            return self

        creative_destination = {c.name: c.destination for c in self.creatives}

        for destination in full_ref_destinations:
            # Every stratum that could publish through this destination, i.e.
            # any stratum naming a creative that names it.
            for stratum in self.strata:
                if not any(
                    creative_destination.get(c) == destination.name
                    for c in stratum.creatives
                ):
                    continue

                # The exact key/value set the ref would carry, assembled the
                # same way create_creative assembles it.
                md = {
                    **stratum.metadata,
                    **self.general.extra_metadata,
                    "form": destination.initial_shortcode,
                    **(destination.additional_metadata or {}),
                }

                unsafe = unsafe_whatsapp_ref_tokens(md)
                if unsafe:
                    raise InvalidConfigError(
                        f"WhatsApp destination '{destination.name}' has "
                        f"include_metadata_in_ref set, but stratum "
                        f"'{stratum.id}' has metadata that fly's WhatsApp entry "
                        f"pattern cannot parse: {unsafe}. Only letters, digits, "
                        "underscore and hyphen survive — a space or a "
                        "percent-sign means the ad silently recruits into the "
                        "fallback survey. Either rename these values or leave "
                        "include_metadata_in_ref off; the ad-ID join carries "
                        "stratum identity to the optimizer either way."
                    )

        return self


# ---------------------------------------------------------------------------
# Completeness check: do the strata demand variables the confs never supply?
#
# A stratum's question_targeting predicate matches on variables that swoosh
# writes into inference_data, and swoosh writes exactly the variables the
# study's inference_data confs name. So a predicate referencing a variable no
# conf produces can never match: the stratum counts zero, and the optimizer
# quietly reallocates its budget elsewhere. Nothing errors. It is the same
# family of silent miscount as an unmapped ad, catchable one layer earlier and
# from configuration alone.
#
# These are pure functions over the conf. Deliberately no raise: see
# missing_targeting_variables for why the caller only warns.
# ---------------------------------------------------------------------------


def targeting_variables(targeting: Optional[QuestionTargeting]) -> set[str]:
    """Every variable name a question_targeting predicate reads.

    Walks the tree, since `vars` holds either leaves (TargetVar) or nested
    QuestionTargeting. Only `type == "variable"` entries name a variable;
    constants are the values compared against.
    """
    if targeting is None:
        return set()

    found: set[str] = set()
    for v in targeting.vars:
        if isinstance(v, QuestionTargeting):
            found |= targeting_variables(v)
        elif v.type == "variable":
            found.add(str(v.value))

    return found


def supplied_variables(conf: Optional[InferenceDataConf]) -> set[str]:
    """Every variable name the study's extraction confs produce.

    Across all locations — "variable", "metadata" and "ad" alike. What matters
    to a predicate is that the variable exists, not where it came from.
    """
    if conf is None:
        return set()

    return {
        ec.name
        for source in conf.data_sources.values()
        for ec in source.extraction_confs
    }


def missing_targeting_variables(study: StudyConf) -> Dict[str, set[str]]:
    """Per stratum, the variables it targets on that nothing supplies.

    Returns only strata with a non-empty gap, so an empty dict means the
    config is complete.

    Returns rather than raises, and callers warn rather than fail. Two reasons.
    A study with no inference_data conf at all supplies nothing, so every
    targeted variable would look missing — that is a study that has not been
    fully configured yet, not a broken one. And this check has never run against
    the thousands of existing production studies, so its false-positive rate is
    unmeasured; turning an unmeasured predicate into a hard failure would stop
    ad reconciliation for any study it misjudges. Measure first, enforce later.
    This mirrors the reasoning in facebook/reconciliation.py:_declared_drop.
    """
    supplied = supplied_variables(study.inference_data)

    gaps = {}
    for stratum in study.strata:
        missing = targeting_variables(stratum.question_targeting) - supplied
        if missing:
            gaps[stratum.id] = missing

    return gaps
