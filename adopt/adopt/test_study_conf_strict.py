"""The write-time models forbid unknown keys, and keep forbidding them.

The interesting test here is the first one. Everything else checks a specific
behaviour; `test_every_nested_model_reachable_from_a_route_is_strict` checks
that the *set* of strict models is still complete, which is the property a
future change is most likely to break silently: add a nested model to a conf
section, forget its twin, and typos inside it go back to being dropped without
anything failing.
"""

from datetime import datetime
from typing import Any, get_args, get_origin

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from .schema_export import CONF_ENDPOINTS
from .study_conf import (
    AudienceConf,
    DestinationConf,
    DestinationRecruitmentExperiment,
    PipelineRecruitmentExperiment,
    RecruitmentConf,
    SimpleRecruitment,
    StratumConf,
)
from .study_conf_strict import (
    RETIRED_DESTINATION_KEYS,
    RETIRED_RECRUITMENT_KEYS,
    STRICT_MODELS,
    AudienceConfStrict,
    DestinationConfStrict,
    RecruitmentConfStrict,
    StratumConfStrict,
)

_START = "2022-01-01T00:00:00"
_END = "2022-03-01T00:00:00"


def _models_reachable_from(annotation: Any) -> set[type[BaseModel]]:
    """Every pydantic model reachable through an annotation, transitively.

    Walks `list[...]`, `dict[...]`, `Optional`/`Union` and `Annotated` alike,
    because a conf section's models hide behind all four -- `DestinationConf`
    is an Annotated union of models inside a list, and
    `InferenceDataConf.data_sources` is a dict whose *values* are models.
    `seen` is not an optimisation: `QuestionTargeting` contains itself.
    """
    seen: set[type[BaseModel]] = set()
    stack = [annotation]

    while stack:
        current = stack.pop()

        # `isinstance(current, type)` is not enough on 3.10: `dict[str, str]`
        # IS an instance of type, and issubclass() then raises rather than
        # returning False. get_origin() is None only for a real, unsubscripted
        # class.
        if (
            isinstance(current, type)
            and get_origin(current) is None
            and issubclass(current, BaseModel)
        ):
            if current in seen:
                continue
            seen.add(current)
            stack.extend(f.annotation for f in current.model_fields.values())
            continue

        # list[X], dict[K, V], Optional[X], Union[...], Annotated[X, ...] --
        # get_args flattens all of them to the types we still care about.
        stack.extend(get_args(current))

    return seen


def test_every_nested_model_reachable_from_a_route_is_strict():
    """No model a POST body can reach may tolerate an unknown key.

    `extra="forbid"` is per-class and does not inherit down into fields, so
    this walks outward from the nine route annotations and checks every model
    it lands on. A new nested model, or a strict twin whose field was not
    re-declared to point at the nested twin, fails here.
    """
    lenient = {}

    for endpoint in CONF_ENDPOINTS:
        for model in _models_reachable_from(endpoint.annotation):
            if model.model_config.get("extra") != "forbid":
                lenient.setdefault(model.__name__, []).append(endpoint.conf_type)

    assert not lenient, (
        "These models are reachable from a POST /confs/<type> body but still "
        f"tolerate unknown keys: {lenient}. Give each one an `XStrict` twin in "
        "adopt/adopt/study_conf_strict.py, and re-declare the field that "
        "points at it so the twin is actually used -- `extra=\"forbid\"` on an "
        "outer class does nothing for the models nested inside it."
    )


def test_strict_models_list_matches_what_the_routes_reach():
    """`STRICT_MODELS` is the module's own inventory; keep it honest.

    The walk above proves nothing lenient is reachable. This proves the
    hand-maintained tuple has not drifted from that set in the other
    direction -- a twin defined and then never wired into a field would
    otherwise sit there looking like coverage it is not providing.
    """
    reachable = set()
    for endpoint in CONF_ENDPOINTS:
        reachable |= _models_reachable_from(endpoint.annotation)

    assert reachable == set(STRICT_MODELS)


# --------------------------------------------------------------------------
# Destinations: the tag is required on a fresh write.
# --------------------------------------------------------------------------


def test_a_typeless_messenger_shaped_destination_is_accepted_and_defaulted():
    """The strict union shares the lenient one's legacy `messenger` default.

    45 stored confs across 11 studies predate the `type` field, and they
    round-trip through the dashboard: it renders no subform for a destination
    whose type it cannot read, so it re-POSTs the conf verbatim. Refusing them
    would make editing destinations impossible on those studies.
    """
    body = [
        {
            "name": "mess",
            "initial_shortcode": "hpv",
            "welcome_message": "Hi",
            "button_text": "Start",
        }
    ]

    written = TypeAdapter(list[DestinationConfStrict]).validate_python(body)[0]

    assert written.type == "messenger"
    # And it is stored with the tag, because create_conf stores model_dump().
    assert written.model_dump()["type"] == "messenger"

    # Same answer on the load path, from the same shared validator.
    assert TypeAdapter(list[DestinationConf]).validate_python(body)[0].type == "messenger"


@pytest.mark.parametrize(
    "shape,body,offending_key",
    [
        (
            "whatsapp",
            {
                "name": "wa",
                "initial_shortcode": "hpv",
                "welcome_message": "Hi",
                "whatsapp_phone_number": "+1-541-920-2635",
            },
            "whatsapp_phone_number",
        ),
        (
            # The 2026-08-30 incident shape: every field messenger requires,
            # PLUS whatsapp_phone_number. Under the old plain union this
            # validated as a Messenger destination, adopt built a MESSENGER ad
            # set for a study configured multi, and Meta rejected every ad.
            "multi",
            {
                "name": "both",
                "initial_shortcode": "hpv",
                "welcome_message": "Hi",
                "button_text": "Start",
                "whatsapp_phone_number": "+1-541-920-2635",
            },
            "whatsapp_phone_number",
        ),
        (
            "web",
            {"name": "site", "url_template": "https://x.example/{ref}"},
            "url_template",
        ),
    ],
)
def test_a_typeless_destination_that_is_not_messenger_shaped_is_rejected(
    shape, body, offending_key
):
    """Why defaulting the tag is safe, and why 422 bought nothing.

    A typeless payload is defaulted to `messenger` and then validated against
    the STRICT messenger twin -- so anything that is not genuinely
    messenger-shaped carries fields messenger does not declare, and those are
    unknown keys. `extra="forbid"` is what closes the hole the discriminator
    was added for; requiring the tag was never what closed it.

    Note the multi case in particular: it satisfies every messenger field, so
    NO amount of required-field checking would catch it. Only forbidding the
    extra does.
    """
    with pytest.raises(ValidationError) as e:
        TypeAdapter(list[DestinationConfStrict]).validate_python([body])

    assert offending_key in str(e.value)


def test_a_retired_destination_key_is_still_accepted():
    """`include_metadata_in_ref` was required until 065bacb8 replaced it with
    `ref_mode`. A stored conf carrying it must not 422 on re-save."""
    body = [
        {
            "type": "web",
            "name": "site",
            "url_template": "https://x.example/{ref}",
            "include_metadata_in_ref": True,
        }
    ]

    dest = TypeAdapter(list[DestinationConfStrict]).validate_python(body)[0]
    assert dest.name == "site"
    assert "include_metadata_in_ref" not in dest.model_dump()
    assert RETIRED_DESTINATION_KEYS == {"include_metadata_in_ref"}


# --------------------------------------------------------------------------
# Recruitment: the legacy shapes, and the over-specified body.
# --------------------------------------------------------------------------


def _common():
    return {
        "objective": "OUTCOME_ENGAGEMENT",
        "optimization_goal": "CONVERSATIONS",
        "min_budget": 100,
        "start_date": _START,
        "end_date": _END,
    }


LEGACY_RECRUITMENT_SHAPES = [
    (
        "simple",
        {**_common(), "ad_campaign_name": "camp", "budget": 1000, "max_sample": 500},
        SimpleRecruitment,
    ),
    (
        "pipeline",
        {
            **_common(),
            "ad_campaign_name_base": "camp",
            "budget_per_arm": 1000,
            "max_sample_per_arm": 500,
            "arms": 3,
            "recruitment_days": 7,
            "offset_days": 7,
        },
        PipelineRecruitmentExperiment,
    ),
    (
        "destination",
        {
            **_common(),
            "ad_campaign_name_base": "camp",
            "budget_per_arm": 1000,
            "max_sample_per_arm": 500,
            "destinations": ["wa", "mess"],
        },
        DestinationRecruitmentExperiment,
    ),
]


@pytest.mark.parametrize("name,body,expected", LEGACY_RECRUITMENT_SHAPES)
def test_an_untagged_recruitment_conf_loads_as_the_arm_it_always_did(
    name, body, expected
):
    """Tagging the union must not restratify a single stored study.

    Every recruitment conf in existence is untagged: the dashboard sent a
    `type` on creation but `extra="ignore"` dropped it before storage. These
    three shapes are what is actually in the corpus, and each has to keep
    resolving to the class it resolves to today, on the LOAD path.
    """
    loaded = TypeAdapter(RecruitmentConf).validate_python(body)
    assert isinstance(loaded, expected)


@pytest.mark.parametrize("name,body,expected", LEGACY_RECRUITMENT_SHAPES)
def test_an_untagged_recruitment_conf_is_still_writable(name, body, expected):
    """And on the WRITE path too, for the same reason plus one more.

    The dashboard's edit path re-POSTs whatever `GET /confs` handed it, which
    for every existing study is one of these untagged shapes. Requiring the tag
    here would 422 every dashboard edit of every study -- so the strict union
    keeps the shape inference, unlike its destination counterpart.
    """
    written = TypeAdapter(RecruitmentConfStrict).validate_python(body)
    assert isinstance(written, expected)


def test_an_over_specified_recruitment_body_is_rejected_on_write():
    """Both `arms` and `destinations` used to resolve to pipeline, silently.

    Union order won and `destinations` was dropped as an extra, so a study
    configured as a destination experiment could run as a pipeline one with
    nothing reporting it (§11.4 item 3). The tag alone does not fix that --
    `extra="forbid"` does, by making the field that does not belong to the
    resolved arm an error that names it.
    """
    body = {
        **_common(),
        "ad_campaign_name_base": "camp",
        "budget_per_arm": 1000,
        "max_sample_per_arm": 500,
        "arms": 3,
        "recruitment_days": 7,
        "offset_days": 7,
        "destinations": ["wa", "mess"],
    }

    with pytest.raises(ValidationError) as e:
        TypeAdapter(RecruitmentConfStrict).validate_python(body)

    assert "destinations" in str(e.value)

    # Unchanged on the load path: it still resolves to pipeline, because
    # changing that would change what an already-stored study means.
    assert isinstance(
        TypeAdapter(RecruitmentConf).validate_python(body),
        PipelineRecruitmentExperiment,
    )


def test_a_retired_recruitment_key_is_still_accepted():
    """`destination_type` was REQUIRED on all three arms until d382000c.

    Every recruitment conf older than 2026-08-30 has it in its stored JSON, and
    the dashboard re-POSTs stored JSON verbatim when you edit a study. Without
    this, extending a study's end date would 422 on the existing corpus.
    """
    body = {
        **_common(),
        "ad_campaign_name": "camp",
        "budget": 1000,
        "max_sample": 500,
        "destination_type": "MESSENGER",
    }

    written = TypeAdapter(RecruitmentConfStrict).validate_python(body)
    assert isinstance(written, SimpleRecruitment)
    assert "destination_type" not in written.model_dump()
    assert RETIRED_RECRUITMENT_KEYS == {"destination_type"}


def test_an_unknown_recruitment_key_is_not_confused_for_a_retired_one():
    """The retired list is a closed set, not a licence to ignore extras."""
    body = {
        **_common(),
        "ad_campaign_name": "camp",
        "budget": 1000,
        "max_sample": 500,
        "destinaton_type": "MESSENGER",  # typo'd, and not on the list
    }

    with pytest.raises(ValidationError) as e:
        TypeAdapter(RecruitmentConfStrict).validate_python(body)

    assert "destinaton_type" in str(e.value)


def test_a_written_tag_is_what_selects_the_arm():
    """Once the tag is present, shape stops mattering -- which is the point.

    A body tagged `destination` that carries pipeline fields is an error rather
    than a pipeline conf, so an author who names the strategy they want cannot
    be given a different one by the field set they happened to send.
    """
    body = {
        **_common(),
        "ad_campaign_name_base": "camp",
        "budget_per_arm": 1000,
        "max_sample_per_arm": 500,
        "arms": 3,
        "recruitment_days": 7,
        "offset_days": 7,
        "type": "destination",
    }

    with pytest.raises(ValidationError) as e:
        TypeAdapter(RecruitmentConfStrict).validate_python(body)

    assert "arms" in str(e.value)


def test_the_tag_is_written_into_storage():
    """`create_conf` stores `model_dump()`, so from now on confs carry a tag.

    That is what eventually makes the shape inference removable.
    """
    dumped = SimpleRecruitment(
        ad_campaign_name="camp",
        objective="OUTCOME_ENGAGEMENT",
        optimization_goal="CONVERSATIONS",
        min_budget=100,
        budget=1000,
        max_sample=500,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 3, 1),
    ).model_dump()

    assert dumped["type"] == "simple"


# --------------------------------------------------------------------------
# Nested strictness, at each of the depths a conf actually has.
# --------------------------------------------------------------------------


def test_a_typo_nested_two_levels_down_is_named_in_the_error():
    """The depth that motivated recursing at all.

    `strata[].question_targeting.vars[].value` is four levels from the request
    body. A misspelling there was accepted and dropped exactly like one at the
    top level, and is likelier -- a hand-written targeting tree is where the
    typing happens.
    """
    body = [
        {
            "id": "s1",
            "quota": 1.0,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"anything_meta_accepts": True},
            "metadata": {},
            "question_targeting": {
                "op": "equal",
                "vars": [{"type": "variable", "value": "age", "valu": "typo"}],
            },
        }
    ]

    with pytest.raises(ValidationError) as e:
        TypeAdapter(list[StratumConfStrict]).validate_python(body)

    assert "valu" in str(e.value)

    # Still accepted by the lenient model the optimizer loads through.
    assert TypeAdapter(list[StratumConf]).validate_python(body)[0].id == "s1"


def test_arbitrary_key_fields_stay_arbitrary():
    """`facebook_targeting` and `metadata` hold keys vlab does not own.

    Meta's spec objects and user-chosen metadata. Forbidding an unknown key
    there would forbid the feature, so recursion has to stop at `Dict[str,
    Any]` rather than treat it as a model with no fields.
    """
    stratum = TypeAdapter(list[StratumConfStrict]).validate_python(
        [
            {
                "id": "s1",
                "quota": 1.0,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {"geo_locations": {"countries": ["NG"]}},
                "metadata": {"whatever_the_researcher_wants": "yes"},
            }
        ]
    )[0]

    assert stratum.facebook_targeting["geo_locations"] == {"countries": ["NG"]}
    assert stratum.metadata["whatever_the_researcher_wants"] == "yes"


def test_a_subtyped_audience_validates_from_raw_json_through_both_models():
    """Fixed here, not merely made strict: it was broken on BOTH paths.

    `AudienceConf.__post_init__` is a `mode="before"` validator, so it sees raw
    input, but it asserted `isinstance(values["lookalike"], Lookalike)` -- that
    the nested value was ALREADY a parsed model. JSON hands it a dict, so a
    LOOKALIKE or PARTITIONED audience could not be written at all, and a stored
    one would have failed `StudyConf` assembly on every cron run. Every test
    built the nested models in Python first, and the dashboard writes neither
    subtype, so nothing ever hit it. `validate()` now checks presence only and
    leaves the shape to the field annotation.
    """
    bodies = [
        [
            {
                "name": "lookalike-of-completers",
                "subtype": "LOOKALIKE",
                "lookalike": {
                    "target": 1000,
                    "spec": {"country": "NG", "ratio": 0.1, "starting_ratio": 0.0},
                },
            }
        ],
        [{"name": "cohorts", "subtype": "PARTITIONED", "partitioning": {"min_users": 100}}],
    ]

    for body in bodies:
        # The write path, and the load path the optimize cron uses.
        assert TypeAdapter(list[AudienceConfStrict]).validate_python(body)
        assert TypeAdapter(list[AudienceConf]).validate_python(body)


def test_a_subtyped_audience_still_needs_the_section_its_subtype_requires():
    """The presence check that survived, and the reason to keep one at all.

    `lookalike` and `partitioning` are `Optional` on the model, so nothing but
    this validator can say that a LOOKALIKE audience without a `lookalike` is
    wrong.
    """
    with pytest.raises(ValidationError) as e:
        TypeAdapter(list[AudienceConfStrict]).validate_python(
            [{"name": "aud", "subtype": "LOOKALIKE"}]
        )

    assert "lookalike" in str(e.value)


def test_a_wrongly_shaped_subtype_section_is_still_rejected():
    """Shape is now the field annotation's job, and it does it.

    Loosening the before-validator to a presence check must not make
    `partitioning: {"foo": "bar"}` acceptable -- it just fails one layer in,
    from `Partitioning`'s own validator instead of from `validate()`.
    """
    with pytest.raises(ValidationError):
        TypeAdapter(list[AudienceConf]).validate_python(
            [{"name": "aud", "subtype": "PARTITIONED", "partitioning": {"foo": "bar"}}]
        )


def test_a_typo_inside_a_lookalike_spec_is_named():
    """Three levels down, and only reachable now that the subtype writes at all.

    `audiences[].lookalike.spec` was unreachable from JSON until the fix above,
    which means the strict twins for `Lookalike` and `LookalikeSpec` had never
    validated anything. This is the test that they do.
    """
    with pytest.raises(ValidationError) as e:
        TypeAdapter(list[AudienceConfStrict]).validate_python(
            [
                {
                    "name": "lal",
                    "subtype": "LOOKALIKE",
                    "lookalike": {
                        "target": 1000,
                        "spec": {
                            "country": "NG",
                            "ratio": 0.1,
                            "starting_ratio": 0.0,
                            "rati": 0.2,
                        },
                    },
                }
            ]
        )

    assert "rati" in str(e.value)
