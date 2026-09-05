"""Write-time twins of the study-configuration models, with `extra="forbid"`.

Why a second set of classes
---------------------------
Every model in `study_conf.py` runs on pydantic's default, `extra="ignore"`, so
a key the model does not declare is accepted and silently discarded. For a
dashboard user that is invisible because the form supplies the field names; for
an agent authoring JSON by hand it is the likeliest failure mode there is, and
vlab's answer was `201 Created` followed by nothing. See
`planning/conf-extra-fields.md` for the investigation and
`planning/agent-study-authoring.md` §11.4 item 2 for why it was blocking.

`extra="forbid"` cannot simply be set on the models themselves, because they are
dual-use. `POST /confs/<type>` stores `config.model_dump()` as raw JSON and
`get_study_conf` reads that same JSON back through the *same class* on every
optimization run (`malaria.py:58`, `malaria.py:576`). Forbidding extras there
would mean that removing or renaming a field stops every conf written before
the change from loading -- halting that study's reconciliation, hours later, in
a cron. `RefModeDestination`'s docstring has said so since before this file
existed.

So: **strict on write, lenient on load.** These classes are used by the nine
`POST /confs/<type>` route annotations in `server/server.py` and nowhere else.
`load_basics`, `get_study_conf`, `get_study_conf_for_reports` and `StudyConf`
keep the lenient classes, unchanged, and keep the forward-compatibility
guarantee that goes with them.

How deep it goes: all the way
-----------------------------
`extra="forbid"` on an outer class says nothing about the models nested inside
it -- a typo at `levels[].facebok_targeting` or
`audiences[].lookalike.spec.rati` is exactly as likely as one at the top level,
and is exactly as silent. So every model reachable from a write-time route has
a strict twin here, and every field whose type is such a model is re-declared
to point at the twin. That re-declaration is the part a future change can
forget, so it is not left to memory:
`test_study_conf_strict.py::test_every_nested_model_reachable_from_a_route_is_strict`
walks the annotations from each route's type and fails if it reaches a model
that is not `extra="forbid"`.

Two kinds of field are deliberately NOT made strict, because they are
arbitrary-key by design rather than by oversight:

  * `FacebookTargeting` / `FacebookAdCreative` (`Dict[str, Any]`) -- these hold
    Meta's own spec objects, whose key set belongs to Meta, not to vlab.
  * `GeneralConf.extra_metadata`, `*.additional_metadata`,
    `StratumConf.metadata` (`dict[str, str]`) -- user-chosen metadata keys.
    Forbidding an unknown key there would forbid the feature.

Naming: `XStrict` subclasses `X`, so a field added to the lenient model is
inherited and needs no edit here.
"""

from typing import Annotated, List, Optional, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .study_conf import (
    AppDestination,
    AudienceConf,
    CreativeConf,
    DataSourceConf,
    DestinationRecruitmentExperiment,
    ExtractionConf,
    ExtractionFunctionConf,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    GeneralConf,
    InferenceDataConf,
    Level,
    Lookalike,
    LookalikeSpec,
    Partitioning,
    PipelineRecruitmentExperiment,
    QuestionTargeting,
    SimpleRecruitment,
    SourceExtractionConf,
    StratumConf,
    TargetVar,
    VariableConf,
    WebDestination,
    _infer_recruitment_type,
)

# One config object, referenced by every class below rather than retyped, so
# "strict" cannot come to mean two slightly different things in one file.
STRICT = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# Retired keys: the one thing `extra="forbid"` must NOT reject.
# --------------------------------------------------------------------------
#
# The dashboard's edit path re-POSTs what `GET /confs` handed it, verbatim
# (e.g. Recruitment.tsx `useState(localData ? localData : ...)`). What
# `GET /confs` hands back is the stored JSON, unvalidated -- which is the last
# successful `model_dump()`, and therefore contains whatever the models
# declared on the day that conf was last saved. So a field this repo has since
# REMOVED is still in the corpus, still round-trips through the dashboard, and
# under a naive `extra="forbid"` would turn "open a study and extend its end
# date" into a 422 on studies that have done nothing wrong.
#
# That is not hypothetical. `destination_type` was a REQUIRED field on all
# three recruitment classes until d382000c (2026-08-30, the commit that
# discriminated the destination union and moved destination_type onto the
# destination where it belongs). Every recruitment conf written before that
# date carries it. `include_metadata_in_ref` was likewise required on the
# destination base until 065bacb8 (2026-08-24), when `ref_mode` replaced it;
# the dashboard never wrote that one, but `copy_confs` and the notebook era
# could have.
#
# These keys are therefore accepted and dropped -- exactly the behaviour they
# have had since the day they were removed, no more and no less. The point of
# naming them instead of leaving `extra="ignore"` on is that the list is
# CLOSED: two names this repo can point at a commit for, versus every possible
# misspelling. A future field removal adds a line here, next to the removal, or
# it breaks the dashboard's edit path -- which is a better prompt than the
# silence there is today.
#
# `planning/conf-extra-fields.md` §5 sketches the production query that would
# say how many stored confs carry each; it has deliberately not been run.
RETIRED_RECRUITMENT_KEYS = frozenset({"destination_type"})
RETIRED_DESTINATION_KEYS = frozenset({"include_metadata_in_ref"})


def _without(value: object, retired: frozenset) -> object:
    """Drop retired keys, leaving anything else for `extra="forbid"` to catch."""
    if not isinstance(value, dict):
        return value
    return {k: v for k, v in value.items() if k not in retired}


# --------------------------------------------------------------------------
# Nested models. Leaf-ward first, so each twin can name the twins it contains.
# --------------------------------------------------------------------------


class TargetVarStrict(TargetVar):
    model_config = STRICT


class QuestionTargetingStrict(QuestionTargeting):
    """Strict, and still self-recursive.

    `vars` holds either a leaf `TargetVar` or another `QuestionTargeting`, to
    arbitrary depth, so the strict twin has to re-declare the field in terms of
    *itself* -- otherwise strictness stops one level down, which is precisely
    where a hand-written targeting tree gets long enough to typo.
    """

    model_config = STRICT

    vars: List[Union[TargetVarStrict, "QuestionTargetingStrict"]]  # type: ignore


class LookalikeSpecStrict(LookalikeSpec):
    model_config = STRICT


class LookalikeStrict(Lookalike):
    model_config = STRICT

    spec: LookalikeSpecStrict


class PartitioningStrict(Partitioning):
    """Strict, but its own before-validator usually reports the typo first.

    `Partitioning.validate_scenario` runs at `mode="before"`, i.e. ahead of
    pydantic's extra-key check, and rejects any combination of set fields that
    is not one of three known scenarios. An unknown key with a non-None value
    therefore fails as "invalid partitioning config, the following fields were
    all set: {...}" rather than "extra inputs are not permitted" -- a different
    message, but one that still names the offending key, which is the property
    that matters. A key whose value is null falls through to the extra check
    and gets the ordinary message.
    """

    model_config = STRICT


class LevelStrict(Level):
    model_config = STRICT


class ExtractionFunctionConfStrict(ExtractionFunctionConf):
    model_config = STRICT


class ExtractionConfStrict(ExtractionConf):
    model_config = STRICT

    functions: list[ExtractionFunctionConfStrict]


class SourceExtractionConfStrict(SourceExtractionConf):
    model_config = STRICT

    extraction_confs: list[ExtractionConfStrict]


# --------------------------------------------------------------------------
# `general`
# --------------------------------------------------------------------------


class GeneralConfStrict(GeneralConf):
    model_config = STRICT


# --------------------------------------------------------------------------
# `recruitment` -- the tagged union, with the tag required on write.
# --------------------------------------------------------------------------


class SimpleRecruitmentStrict(SimpleRecruitment):
    model_config = STRICT


class PipelineRecruitmentExperimentStrict(PipelineRecruitmentExperiment):
    model_config = STRICT


class DestinationRecruitmentExperimentStrict(DestinationRecruitmentExperiment):
    model_config = STRICT


# The strict recruitment union KEEPS the shape inference, unlike its
# destination counterpart below, and the asymmetry is deliberate.
#
# A destination conf has carried an explicit `type` from every writer for years;
# only stored confs predating the field lack one, and no fresh write should.
# Recruitment is the opposite: the dashboard sends `type` when you first pick a
# strategy, but when you EDIT an existing conf it re-renders whatever
# `GET /confs` returned (Recruitment.tsx, `useState(localData ? localData :
# ...)`) -- and until this change `extra="ignore"` dropped the tag before it was
# ever stored, so every recruitment conf in existence reads back untagged.
# Requiring the tag here would 422 every dashboard edit of every study, which is
# not a defect an agent's typo is worth causing.
#
# Nothing is lost by inferring it. What §11.4 item 3 actually asked for is that
# an over-specified body stop resolving silently to the wrong arm, and
# `extra="forbid"` is what delivers that: a body carrying both `arms` and
# `destinations` infers the pipeline arm exactly as today, and then fails with
# "extra inputs are not permitted: destinations" instead of dropping it. The
# inference can be deleted once every stored recruitment conf carries a real
# tag -- which starts happening with this change, since `model_dump()` now
# writes one.
def _prepare_recruitment_write(value: object) -> object:
    """Drop retired keys, then infer the tag. One function, so the order is
    stated rather than left to how pydantic composes stacked validators."""
    return _infer_recruitment_type(_without(value, RETIRED_RECRUITMENT_KEYS))


RecruitmentConfStrict = Annotated[
    Annotated[
        Union[
            SimpleRecruitmentStrict,
            PipelineRecruitmentExperimentStrict,
            DestinationRecruitmentExperimentStrict,
        ],
        Field(discriminator="type"),
    ],
    BeforeValidator(_prepare_recruitment_write),
]


# --------------------------------------------------------------------------
# `destinations` -- the tagged union, with NO legacy default for a missing tag.
# --------------------------------------------------------------------------


class FlyMessengerDestinationStrict(FlyMessengerDestination):
    model_config = STRICT


class WebDestinationStrict(WebDestination):
    model_config = STRICT


class AppDestinationStrict(AppDestination):
    model_config = STRICT


class FlyWhatsAppDestinationStrict(FlyWhatsAppDestination):
    model_config = STRICT


class FlyMultiDestinationStrict(FlyMultiDestination):
    model_config = STRICT


# NO `_default_missing_destination_type` here, deliberately -- this is the one
# place the strict union differs from the lenient one in more than extra-key
# handling.
#
# That BeforeValidator exists for 45 stored confs across 11 studies that predate
# the `type` field, and it fills in "messenger" so they keep LOADING as what
# they have always been. A fresh write is not that situation: nothing being
# POSTed today predates the field, so a body arriving here with no `type` is an
# author who forgot it, not history. Defaulting it would hand that author a
# Messenger destination they did not ask for and a `201` saying it worked --
# the same class of silent mis-resolution the discriminator was added to stop
# (study_conf.py, the comment above `_TaggedDestination`). Without the default
# they get a 422 saying "Unable to extract tag using discriminator 'type'".
#
# The known cost, recorded rather than discovered later: the 45 typeless confs
# DO round-trip through the dashboard, because a destination whose `type` it
# cannot read renders no subform and is re-POSTed verbatim. Editing destinations
# on one of those 11 studies now returns that 422 instead of silently re-saving
# a Messenger destination. That is the right failure -- the dashboard could not
# show the user what they were saving either -- and the remedy is to pick a type
# once, which also fixes the display.
#
# Settles planning/conf-extra-fields.md §6 question 2.
DestinationConfStrict = Annotated[
    Annotated[
        Union[
            FlyMessengerDestinationStrict,
            AppDestinationStrict,
            WebDestinationStrict,
            FlyWhatsAppDestinationStrict,
            FlyMultiDestinationStrict,
        ],
        Field(discriminator="type"),
    ],
    BeforeValidator(lambda v: _without(v, RETIRED_DESTINATION_KEYS)),
]


# --------------------------------------------------------------------------
# The remaining five sections.
# --------------------------------------------------------------------------


class CreativeConfStrict(CreativeConf):
    # `arbitrary_types_allowed` has to be carried forward by hand: assigning
    # `model_config` in a subclass REPLACES the parent's rather than merging
    # into it, and `template` is a `FacebookAdCreative` alias that needs it.
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class AudienceConfStrict(AudienceConf):
    model_config = STRICT

    question_targeting: Optional[QuestionTargetingStrict] = None
    lookalike: Optional[LookalikeStrict] = None
    partitioning: Optional[PartitioningStrict] = None


class VariableConfStrict(VariableConf):
    """Strict via a sibling, like everything else, rather than in place.

    `planning/conf-extra-fields.md` §2 notes that `VariableConf` is the one
    model with no load path -- it is not a field of `StudyConf` and is read
    back only as raw JSON -- so it could take `extra="forbid"` directly, with
    no sibling needed. It gets one anyway, for two reasons. The licence rests
    on a fact about today ("nothing reconstructs a VariableConf from storage"),
    not on a property of the model, and a `POST /studies/{slug}/validate`
    endpoint that re-reads stored confs is being built in parallel with this
    change. And a single uniform mechanism means nobody has to remember which
    one model is the exception, for a cost of four lines.
    """

    model_config = STRICT

    levels: list[LevelStrict]


class StratumConfStrict(StratumConf):
    model_config = STRICT

    question_targeting: Optional[QuestionTargetingStrict] = None


class DataSourceConfStrict(DataSourceConf):
    model_config = STRICT


class InferenceDataConfStrict(InferenceDataConf):
    model_config = STRICT

    data_sources: dict[str, SourceExtractionConfStrict]


# `QuestionTargetingStrict` names itself in its own annotation, and this file
# has no `from __future__ import annotations`, so the forward reference has to
# be resolved once the class exists.
QuestionTargetingStrict.model_rebuild()


# Every model this module makes strict, for the guard test. Listing them is
# what lets that test assert the set is COMPLETE (every nested model reachable
# from a route is here) rather than merely non-empty.
STRICT_MODELS: tuple[type[BaseModel], ...] = (
    TargetVarStrict,
    QuestionTargetingStrict,
    LookalikeSpecStrict,
    LookalikeStrict,
    PartitioningStrict,
    LevelStrict,
    ExtractionFunctionConfStrict,
    ExtractionConfStrict,
    SourceExtractionConfStrict,
    GeneralConfStrict,
    SimpleRecruitmentStrict,
    PipelineRecruitmentExperimentStrict,
    DestinationRecruitmentExperimentStrict,
    FlyMessengerDestinationStrict,
    WebDestinationStrict,
    AppDestinationStrict,
    FlyWhatsAppDestinationStrict,
    FlyMultiDestinationStrict,
    CreativeConfStrict,
    AudienceConfStrict,
    VariableConfStrict,
    StratumConfStrict,
    DataSourceConfStrict,
    InferenceDataConfStrict,
)
