from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from math import floor
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, model_serializer, model_validator

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


# The values `ExtractionConf.mapping` takes. Mirrored in swoosh
# (inference/swoosh/inference_data.go); these two lists are the contract.
MAPPING_RAW = "raw"
MAPPING_AD_TABLE_LOOKUP = "ad_table_lookup"
MAPPINGS = (MAPPING_RAW, MAPPING_AD_TABLE_LOOKUP)


class ExtractionConf(BaseModel):
    """One declared variable: where to read it, and what to do with what is read.

    `location` says where to read -- "metadata" or "variable". `mapping` says
    what the read value means:

        "raw"             the value read IS the answer. The default, and what
                          every conf written before this field existed means.
        "ad_table_lookup" the value read is an opaque token; the answer is a
                          stratum variable off the frozen ad_attributions row
                          that token identifies.

    `key` and `name` are both contextual to the mapping, which is the one
    genuinely confusing part of this:

        key   WHERE TO READ, within the location. For "raw" it addresses the
              value; for a lookup it addresses the token. Never hardcoded --
              fly stamps the token at metadata.vt by convention and the conf
              says key: "vt" to match, while a platform returning it as a
              survey answer declares location "variable" and that field's name.
        name  the output variable name and, for a lookup, ALSO the key into the
              frozen row (which stratum variable to pull). It does double duty
              because you name the output after the stratum variable anyway.
    """

    location: str
    mapping: str = MAPPING_RAW
    key: str
    name: str
    functions: list[ExtractionFunctionConf]
    value_type: str
    aggregate: str

    @model_validator(mode="after")
    def mapping_must_be_known(self):
        if self.mapping not in MAPPINGS:
            raise ValueError(
                f"Extraction conf '{self.name}' has mapping: "
                f"\"{self.mapping}\", which is not one of {list(MAPPINGS)}."
            )
        return self

    @property
    def is_ad_table_lookup(self) -> bool:
        """Whether this conf resolves through the ad table.

        The mapping alone decides it. Location and mapping are independent
        axes: a platform that returns the token as a survey field declares
        `variable`, one that stamps it on the event declares `metadata`, and
        the lookup that follows is the same either way.
        """
        return self.mapping == MAPPING_AD_TABLE_LOOKUP


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


# How a fly destination serialises its ad's routing token. Two modes, and a
# destination is in exactly one of them.
#
#   "metadata"  the historical dotted ref: `creative.<name>.<k>.<v>...`. Carries
#               the study's stratum inline, so attribution needs no join. A
#               study with no stratification just gets a short one.
#   "encoded"   `r.<base64url(v1|len|shortcode|token)>`. Routes AND carries an
#               opaque join key, so attribution does not depend on Meta sending
#               a referral -- which it does for only ~31% of Messenger ad
#               entrants (documentation/recruitment-arrival-health.md).
#
# A ref either carries the stratum inline, or carries a token that resolves to
# it. There is no third answer: "carry neither" is a ref that attributes nobody,
# which is not something anyone chooses -- a study with no stratification simply
# has a short ref, because creative_metadata has nothing to put in it. That is
# thick with nothing to say, not a mode of its own.
#
# "encoded" exists because inline stratum values are visible and editable by the
# respondent wherever the ref is (WhatsApp's compose box), and because they ship
# vlab's stratum vocabulary into fly on every message. The token rides a carrier
# vlab authors, so it reaches everyone while disclosing nothing.
RefMode = Literal["metadata", "encoded"]


class RefModeDestination(BaseModel):
    """Shared ref-mode resolution for every destination type.

    A base rather than a copy per class because the modes must not drift: every
    consumer -- marketing, the half-migration guard, reconciliation -- asks
    `resolved_ref_mode`, and a destination type that answered differently would
    be a silent routing difference between channels.

    Every type, including web and app. What a ref carries is a property of the
    ref, not of the channel that carries it: an ad either ships the stratum
    inline or ships a token that resolves to it, and that is the same choice
    wherever the ad points. Whether anything reads the token back is the read
    side's business and is configured there.
    """

    # None means "not stated", which is what every conf written before this
    # field existed carries. Optional rather than defaulted to a mode is what
    # keeps the migration free: an untouched conf resolves to exactly the
    # behaviour it has today, without anyone rewriting stored JSON.
    ref_mode: Optional[RefMode] = None

    @property
    def resolved_ref_mode(self) -> str:
        """The mode this destination actually serialises under.

        The single source of truth, and now a one-liner: an unstated mode is a
        conf that predates the field, and every such conf carries the stratum
        inline.

        This used to resolve through `include_metadata_in_ref`, a boolean that
        expressed the same setting a second way and could not express "encoded".
        It is gone, and nothing stored carries it: it was never deployed. The
        mode it selected -- carry neither the stratum nor a token -- was not a
        coherent thing to ask for, so there is no third answer to give here.
        """
        return self.ref_mode or "metadata"


class FlyMessengerDestination(RefModeDestination):
    type: str
    name: str
    initial_shortcode: str
    welcome_message: str
    button_text: str
    additional_metadata: Optional[dict[str, str]] = None


class WebDestination(RefModeDestination):
    type: str
    name: str
    url_template: str  # create variables, like ref, which can be used.


class AppDestination(RefModeDestination):
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
#     /^(?:start\s+)?form\.((?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+
#                           (?:\.(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+)*)$/i
#
# Two consequences, both verified against that regex:
#
# 1. The token must lead with `form.`. `make_ref` leads with `creative.`, so its
#    output can never match, whatever the values are. A WhatsApp ref has to be
#    serialised form-first.
# 2. Every token is `[A-Za-z0-9_-]` or a percent-encoded octet. The gate was
#    widened to accept `%XX` on fly@feature/ad-id-attribution 37e1e06e, which
#    is what makes encoded values travel — before that a space was undeliverable
#    raw *and* encoded, and roughly half of real stratum values could not be
#    shipped at all.
#
# A failure here is silent and expensive: Meta delivers the text intact (dots
# and spaces both survive `autofill_message.content`, measured), fly's pattern
# rejects it, no conversation_started is derived, and the arrival falls through
# to FALLBACK_FORM — a real survey, so the respondents look like completions
# rather than errors. That is the VIR-19 failure shape. Hence: validate at
# config time, never emit and hope.
WHATSAPP_REF_TOKEN = re.compile(r"^(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+$")

# The shortcode keeps the *narrow* alphabet, deliberately, even though the gate
# would now accept it encoded.
#
# Metadata values are only ever transported by an ad, so encoding is enough for
# them. A shortcode is also typed by a human: shortcodes are designed to be
# shareable, and someone who hears about a study texts `form.<shortcode>`
# straight into WhatsApp. That hand-typed message carries a literal space, not
# `%20`, so it fails the gate and the person lands in FALLBACK_FORM. A
# shortcode therefore has to be typeable as-is, not merely encodable.
WHATSAPP_SHORTCODE_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def ref_value(value: str) -> str:
    """Encode one metadata value for a dotted ref.

    `quote()` alone is not enough. Python keeps `.`, `-`, `_` and `~` in
    urllib's `_ALWAYS_SAFE`, and passing `safe=''` does *not* override that —
    measured: `quote('a.b') == 'a.b'`, `quote('x~y') == 'x~y'`. Two of those
    four break a ref:

      `.` is the ref's own separator, so a dotted value silently mis-pairs
          every key/value after it when fly's `_group` walks the tokens. That
          is the corruption found in phase 1, now explained rather than merely
          observed.
      `~` is absent from fly's WhatsApp token alphabet, so it fails the entry
          gate outright and the arrival falls through to FALLBACK_FORM.

    `-` and `_` are both separator-safe and inside the gate alphabet, so they
    are deliberately left alone; encoding them would churn refs for no gain.

    Escaping after quoting is safe: `quote()` has already turned any literal
    `%` into `%25`, so no `.` or `~` can be sitting inside an escape sequence.

    Lives here rather than next to `make_ref` because the config-time WhatsApp
    deliverability check needs it and study_conf cannot import marketing.
    """
    return quote(value).replace(".", "%2E").replace("~", "%7E")


def whatsapp_ref_token_safe(value: str) -> bool:
    """True if `value` survives fly's WhatsApp entry pattern once encoded.

    Checked against the *encoded* form, because that is what the ad ships.
    Before fly widened the gate this had to be checked raw, which made roughly
    half of real stratum values undeliverable. What still fails is only what
    `quote()` leaves literal and the gate does not accept — in practice just
    `/`, which `quote()` keeps by default.
    """
    return bool(WHATSAPP_REF_TOKEN.match(ref_value(value)))


def whatsapp_shortcode_safe(shortcode: str) -> bool:
    """True if `shortcode` survives the gate *and* a human typing it by hand."""
    return bool(WHATSAPP_SHORTCODE_TOKEN.match(shortcode))


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

# The single ad-set destination_type token each fly destination implies.
#
# These are the values Meta's destination_type guide defines; the combination
# tokens are single enum values, not lists. There is no `messaging_apps` field
# and no list-valued destination field — see planning/click-to-whatsapp-ads.md
# §1.2, which says so explicitly because it is an easy thing to look for.
MESSENGER_DESTINATION_TYPE = "MESSENGER"
WHATSAPP_DESTINATION_TYPE = "WHATSAPP"
MULTI_DESTINATION_TYPE = "MESSAGING_MESSENGER_WHATSAPP"

# Every destination_type that routes to a messaging app. A recruitment conf
# naming one of these is making a claim about the channel its ads open, and
# that claim is checkable against the destinations the study actually declares.
# A recruitment conf naming anything else (WEB, WEBSITE, APP, ...) makes no such
# claim, so nothing is checked and the ad-set value is derived instead.
MESSAGING_DESTINATION_TYPES = {MESSENGER_DESTINATION_TYPE} | WHATSAPP_DESTINATION_TYPES


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


class FlyWhatsAppDestination(RefModeDestination):
    """A click-to-WhatsApp destination.

    Shaped after FlyMessengerDestination, minus `button_text` (WhatsApp has no
    quick-reply button; the respondent gets a prefilled compose box) and plus
    the number the ad's clicks land on.

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
        if not whatsapp_shortcode_safe(self.initial_shortcode):
            raise InvalidConfigError(
                f"WhatsApp destination '{self.name}': initial_shortcode "
                f"'{self.initial_shortcode}' contains characters fly's WhatsApp "
                "entry pattern rejects when typed by hand. Only letters, "
                "digits, underscore and hyphen. Metadata values may now be "
                "percent-encoded, but a shortcode may not: it is meant to be "
                "shareable, and someone texting it straight into WhatsApp "
                "sends a literal space, which lands them in the fallback "
                "survey instead of yours."
            )
        return self


class FlyMultiDestination(RefModeDestination):
    """A single ad that opens either Messenger or WhatsApp, Meta's choice.

    A third destination type, deliberately, rather than a `platforms` list on a
    merged class or an implicit consequence of the ad set's destination_type.
    The reasoning is in planning/whatsapp-destination-model.md: Messenger and
    WhatsApp differ in the grammar their routing token must obey, in whether the
    respondent can see and edit it, in which fields are required, and in what a
    misconfiguration costs. Multi is not the generalisation of the two -- it is
    a third thing that carries both of their tokens at once, and it forecloses
    something they each allow (channel as an experimental arm, since Meta
    assigns the arm and you cannot randomise what Meta assigns).

    One shortcode, not one per channel. `creative_metadata` folds
    `form: initial_shortcode` into the frozen ad_attributions blob, and there is
    exactly one blob per ad; a per-channel shortcode would mean one ad whose two
    arms belong to two surveys and one mapping row that can only name one of
    them.

    Encoded is the sensible mode here, because the WhatsApp arm's ref sits in
    the respondent's compose box where they can read and edit it. Being
    described back to yourself as `gender.men.age.25_34` before a survey starts
    is an ethical question, not a technical one.

    Asymmetric confidence between the two arms. The Messenger arm is MEASURED:
    on 2026-08-17 ad 120254903561240150 delivered its quick-reply payload with
    the ref intact even though `text_format.customer_action_type` was the scalar
    "autofill_message", so Messenger reads its own sub-structure and ignores the
    sibling autofill (planning/whatsapp-destination-model.md 8.1). The WhatsApp
    arm rests on the symmetry inference from that result and has not itself been
    observed -- every preview followed the single-valued MESSAGE_PAGE
    call_to_action to Messenger. If the inference is wrong and Meta serves its
    own default prefill, fly's event-normalizer still emits
    conversation_started, and those arrivals land on FALLBACK_FORM: a real
    survey belonging to another researcher, where misrouted respondents reach
    END and look like completions. Watch the WhatsApp arm of the first multi
    study for that shape; documentation/multi-destination-ads.md has the
    procedure.
    """

    type: Literal["multi"]
    name: str
    initial_shortcode: str
    welcome_message: str

    # The Messenger arm's quick-reply button. Measured to be the carrier 68% of
    # Messenger ad entrants route through -- and their ONLY carrier, since they
    # produce no OPEN_THREAD referral at all. Required for that reason: a multi
    # ad without it loses two thirds of its Messenger arm to FALLBACK_FORM.
    button_text: str

    # The WhatsApp arm's promoted_object, exactly as FlyWhatsAppDestination.
    whatsapp_phone_number: str

    additional_metadata: Optional[dict[str, str]] = None

    @property
    def promoted_phone_number(self) -> str:
        """The number in the form Meta's promoted_object wants."""
        return normalize_whatsapp_phone_number(self.whatsapp_phone_number)

    @model_validator(mode="after")
    def phone_number_must_be_dialable(self):
        if not whatsapp_phone_number_valid(self.whatsapp_phone_number):
            raise InvalidConfigError(
                f"Multi destination '{self.name}': whatsapp_phone_number "
                f"'{self.whatsapp_phone_number}' is not a dialable number. Meta "
                "wants the number itself (any punctuation is fine, it is "
                "stripped), not the phone_number_id."
            )
        return self

    @model_validator(mode="after")
    def shortcode_must_survive_the_entry_pattern(self):
        # Same narrow alphabet as FlyWhatsAppDestination, for the same reason:
        # this destination has a WhatsApp arm, and a shortcode is meant to be
        # shareable. Someone who hears about the study and texts
        # `form.<shortcode>` by hand sends a literal space, not %20.
        if not whatsapp_shortcode_safe(self.initial_shortcode):
            raise InvalidConfigError(
                f"Multi destination '{self.name}': initial_shortcode "
                f"'{self.initial_shortcode}' contains characters fly's WhatsApp "
                "entry pattern rejects when typed by hand. Only letters, digits, "
                "underscore and hyphen."
            )
        return self


DestinationConf = Union[
    FlyMessengerDestination,
    AppDestination,
    WebDestination,
    FlyWhatsAppDestination,
    FlyMultiDestination,
]


def destination_type_for(destination: DestinationConf) -> Optional[str]:
    """The ad set destination_type this destination requires, or None.

    `destination_type` is an ad-set field while destinations are named per
    creative, so channel is necessarily uniform within a stratum and something
    has to agree the value across the stratum's pairs. This is the per-pair half
    of that, shaped exactly like `promoted_object_for`.

    None means "this destination does not care": Web and App encode their target
    in a URL or deeplink and are indifferent to how Meta labels the ad set, so
    the recruitment conf's value governs. That is what keeps the 5 studies whose
    recruitment conf says WEB or WEBSITE producing byte-identical ad sets.
    """
    if isinstance(destination, FlyMessengerDestination):
        return MESSENGER_DESTINATION_TYPE

    if isinstance(destination, FlyWhatsAppDestination):
        return WHATSAPP_DESTINATION_TYPE

    if isinstance(destination, FlyMultiDestination):
        return MULTI_DESTINATION_TYPE

    return None


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
    def check_destination_type_matches_destinations(self):
        """A messaging destination_type must be backed by a real destination.

        `destination_type` used to be checked in exactly one direction: a
        WhatsApp destination had to sit on a WhatsApp-capable ad set. The mirror
        never fired, so two silent misroutes were reachable today:

          - `MESSAGING_MESSENGER_WHATSAPP` with only Messenger destinations.
            The ads run multi-destination, the Messenger arm keeps its
            quick-reply welcome message and routes fine, and the WhatsApp arm
            has no autofill token at all -- so every WhatsApp clicker Meta
            routes there lands on FALLBACK_FORM. Half the ad works, which is
            why the operator has no reason to suspect it.
          - the same with only WhatsApp destinations, which passed because the
            old check only asked whether the value was WhatsApp-*capable*.

        The rule now: if the recruitment conf names a messaging destination_type
        it is making a claim about the channel its ads open, and some
        destination in the study must actually imply that exact token. A
        recruitment conf naming WEB, WEBSITE or APP makes no such claim, so
        nothing is checked and `adset_destination_type` derives the value
        instead -- which is what keeps the five legacy studies whose recruitment
        conf says WEB or WEBSITE building exactly as they always have.

        Deliberately "some destination", not "every destination": a study with a
        Messenger arm and a WhatsApp arm is the whole point of deriving the type
        per ad set, and it necessarily has destinations that disagree with each
        other. Disagreement *within one stratum* is the real error, and
        `adset_destination_type` raises on it where it can actually be seen.

        And deliberately silent for a study with no fly destination at all —
        including one whose destinations conf is empty, which is a study still
        being assembled rather than a broken one. A web-only or app-only study
        does not open a conversation, so its destination_type makes no claim
        this check can hold it to, and such studies do exist with a messaging
        destination_type stored, harmlessly, because nothing ever validated it.
        Every failure this check exists to catch involves at least one fly
        destination.
        """
        destination_type = self.recruitment.destination_type

        if destination_type not in MESSAGING_DESTINATION_TYPES:
            return self

        implied = {
            t
            for t in (destination_type_for(d) for d in self.destinations)
            if t is not None
        }

        if not implied:
            return self

        if destination_type in implied:
            return self

        named = sorted(implied)
        raise InvalidConfigError(
            f"This study's recruitment destination_type is "
            f"'{destination_type}', but none of its destinations open that "
            f"channel — they imply {named or 'no messaging channel at all'}. "
            "Meta routes the ad set by destination_type, so the arm that has "
            "no destination behind it carries no routing token: those "
            "respondents start a conversation and fall through to the fallback "
            "survey, where they look like completions rather than errors. "
            "Either point a destination at that channel or set "
            "destination_type to one the destinations actually provide."
        )

    @model_validator(mode="after")
    def check_multi_destination_optimization_goal(self):
        """Multi-destination forces CONVERSATIONS, per Meta's own guide.

        This is the coupling cost of multi: a destination choice constrains an
        unrelated-looking, study-level recruitment setting. Validated here, with
        a message naming both fields, rather than letting Meta reject the ad set
        later with an error that never mentions the destination.

        Checked rather than silently overridden. `optimization_goal` is a
        deliberate study setting -- it is what the optimizer's cost-per-
        respondent is measured against -- and quietly rewriting it would change
        what a study buys without telling anyone.

        Worth knowing before this fires on you: Meta's guide calls
        CONVERSATIONS mandatory, but this repo has measured
        `MESSAGING_MESSENGER_WHATSAPP` + `LINK_CLICKS` being *accepted* on a
        live ad set (planning/click-to-whatsapp-ads.md §6a), and separately that
        a Page subject to European privacy rules cannot use CONVERSATIONS for
        click-to-WhatsApp at all. So on such a Page the two constraints
        genuinely conflict and no multi ad can be configured -- which is a real
        finding about the Page, and much better surfaced here than discovered
        halfway through a reconciliation run.
        """
        if not any(isinstance(d, FlyMultiDestination) for d in self.destinations):
            return self

        goal = self.recruitment.optimization_goal
        if goal != "CONVERSATIONS":
            raise InvalidConfigError(
                f"This study has a multi-destination destination but its "
                f"recruitment optimization_goal is '{goal}'. Meta requires "
                "CONVERSATIONS for multi-destination ad sets. Set "
                "optimization_goal to CONVERSATIONS, or use single-destination "
                "Messenger and WhatsApp destinations instead — note that a Page "
                "subject to European privacy rules cannot use CONVERSATIONS for "
                "click-to-WhatsApp at all, in which case multi-destination is "
                "not configurable on that Page."
            )

        return self

    @model_validator(mode="after")
    def check_whatsapp_refs_are_deliverable(self):
        """Reject a full-metadata WhatsApp ref that fly could never parse.

        Only fires for a WhatsApp destination carrying the stratum inline,
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
        # Multi is included: its WhatsApp arm ships the same form-first autofill
        # through the same fly entry pattern, so an unparseable value fails
        # there in exactly the same way — and on multi it fails on one arm only,
        # which is harder to notice, not easier.
        full_ref_destinations = [
            d
            for d in self.destinations
            if isinstance(d, (FlyWhatsAppDestination, FlyMultiDestination))
            and d.resolved_ref_mode == "metadata"
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
                        f"its stratum inline in the ref, but stratum "
                        f"'{stratum.id}' has metadata that fly's WhatsApp entry "
                        f"pattern cannot parse: {unsafe}. Only letters, digits, "
                        "underscore and hyphen survive — a space or a "
                        "percent-sign means the ad silently recruits into the "
                        "fallback survey. Either rename these values or use "
                        "ref_mode 'encoded'; the ad-attributions join carries "
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

    Across every location and mapping alike — raw metadata, a survey variable,
    or an ad_table_lookup. What matters to a predicate is that the variable
    exists, not where it came from.
    """
    if conf is None:
        return set()

    return {
        ec.name
        for source in conf.data_sources.values()
        for ec in source.extraction_confs
    }


def thins_its_ref_without_reading_the_mapping(study: StudyConf) -> List[str]:
    """Destinations that stop carrying metadata while nothing reads the mapping.

    Thinning the ref is what finally makes the ad table *replace* the ref
    rather than duplicate it — but it only works if the study also reads the
    mapping, via at least one `mapping: "ad_table_lookup"` extraction conf. Do
    one without the other and the study has no attribution at all: the ref no
    longer carries the stratum, and nothing looks the token up. Every stratum
    counts zero and the optimizer reallocates on empty data.

    Returns destination names rather than raising, because it is not certainly
    wrong: a study recruiting uniformly, with no question_targeting, needs no
    stratum attribution and is entitled to a thin ref. Same reasoning as
    missing_targeting_variables.

    """
    thinned = [
        d.name for d in study.destinations if d.resolved_ref_mode != "metadata"
    ]

    if not thinned:
        return []

    reads_the_mapping = any(
        ec.is_ad_table_lookup
        for source in (study.inference_data.data_sources.values() if study.inference_data else [])
        for ec in source.extraction_confs
    )

    return [] if reads_the_mapping else sorted(thinned)


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
