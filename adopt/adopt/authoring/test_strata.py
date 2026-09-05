"""Translation of `dashboard/src/pages/StudyConfPage/forms/strata/strata.spec.ts`.

One pytest function per `it(...)` in the spec, in spec order, with the expected
values copied across literally -- these are the conformance suite for
`strata.py`, and paraphrasing a case would quietly weaken it. Cases that exist
only in Python, covering behaviour the TypeScript left implicit, are in the
clearly marked section at the bottom.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from .strata import (
    create_strata_from_variables,
    format_group_product,
    get_finish_question_ref,
    strata_staleness_hint,
)

# ---------------------------------------------------------------------------
# describe('createStrataFromVariables')
# ---------------------------------------------------------------------------


def test_empty_variables_create_empty_strata():
    variables: list = []
    creatives = None
    # The spec passes `creatives` where `finishQuestionRef` goes; kept as-is,
    # since it is exactly what makes this a two-falsy-guards test.
    strata = create_strata_from_variables(variables, creatives)

    assert strata == []


def test_works_with_one_variable_and_multiple_levels():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        }
    ]

    creatives: list = []
    strata = create_strata_from_variables(variables, "foo", creatives)

    assert strata == [
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "men"},
            "creatives": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.5,
            "id": "gender:men",
        },
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "women"},
            "creatives": [],
            "facebook_targeting": {"genders": [2]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "women"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.5,
            "id": "gender:women",
        },
    ]


def test_works_with_one_variable_and_one_level():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 1.0,
                }
            ],
        }
    ]

    creatives: list = []
    strata = create_strata_from_variables(variables, "foo", creatives)

    assert strata == [
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "men"},
            "creatives": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 1.0,
            "id": "gender:men",
        }
    ]


def test_creates_product_of_two_variables_and_multiple_levels():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        },
        {
            "name": "age",
            "properties": ["age_min", "age_max"],
            "levels": [
                {
                    "name": "18",
                    "template_campaign": "foo",
                    "template_adset": "18-34",
                    "facebook_targeting": {"age_min": 18, "age_max": 34},
                    "quota": 0.5,
                },
                {
                    "name": "35",
                    "template_campaign": "foo",
                    "template_adset": "35-65",
                    "facebook_targeting": {"age_min": 35, "age_max": 65},
                    "quota": 0.5,
                },
            ],
        },
    ]

    creatives = None
    strata = create_strata_from_variables(variables, "foo", creatives)

    assert strata == [
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "men", "age": "18"},
            "creatives": [],
            "facebook_targeting": {"genders": [1], "age_min": 18, "age_max": 34},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "18"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.25,
            "id": "gender:men,age:18",
        },
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "men", "age": "35"},
            "creatives": [],
            "facebook_targeting": {"genders": [1], "age_min": 35, "age_max": 65},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "35"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.25,
            "id": "gender:men,age:35",
        },
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "women", "age": "18"},
            "creatives": [],
            "facebook_targeting": {"genders": [2], "age_min": 18, "age_max": 34},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "women"},
                        ],
                    },
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "18"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.25,
            "id": "gender:women,age:18",
        },
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "women", "age": "35"},
            "creatives": [],
            "facebook_targeting": {"genders": [2], "age_min": 35, "age_max": 65},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "women"},
                        ],
                    },
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "35"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.25,
            "id": "gender:women,age:35",
        },
    ]


def test_creates_product_of_three_variables_and_multiple_levels():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        },
        {
            "name": "age",
            "properties": ["age_min", "age_max"],
            "levels": [
                {
                    "name": "18",
                    "template_campaign": "foo",
                    "template_adset": "18-34",
                    "facebook_targeting": {"age_min": 18, "age_max": 34},
                    "quota": 0.5,
                },
                {
                    "name": "35",
                    "template_campaign": "foo",
                    "template_adset": "35-65",
                    "facebook_targeting": {"age_min": 35, "age_max": 65},
                    "quota": 0.5,
                },
            ],
        },
        {
            "name": "location",
            "properties": ["geo_location"],
            "levels": [
                {
                    "name": "foo",
                    "template_campaign": "foo",
                    "template_adset": "foo",
                    "facebook_targeting": {"geo_location": {"city": "foo"}},
                    "quota": 0.5,
                },
                {
                    "name": "bar",
                    "template_campaign": "foo",
                    "template_adset": "bar",
                    "facebook_targeting": {"geo_location": {"city": "bar"}},
                    "quota": 0.5,
                },
                {
                    "name": "baz",
                    "template_campaign": "foo",
                    "template_adset": "baz",
                    "facebook_targeting": {"geo_location": {"city": "baz"}},
                    "quota": 0.5,
                },
            ],
        },
    ]

    creatives = None
    strata = create_strata_from_variables(variables, "foo", creatives)

    assert len(strata) == 12
    assert len([s for s in strata if s["facebook_targeting"]["age_min"] == 35]) == 6
    assert len([s for s in strata if s["facebook_targeting"]["age_min"] == 18]) == 6
    assert len([s for s in strata if s["facebook_targeting"]["genders"][0] == 1]) == 6
    assert len([s for s in strata if s["facebook_targeting"]["genders"][0] == 2]) == 6
    cities = [s["facebook_targeting"]["geo_location"]["city"] for s in strata]
    assert cities.count("foo") == 4
    assert cities.count("bar") == 4
    assert cities.count("baz") == 4


# ---------------------------------------------------------------------------
# describe('getFinishQuestionRef')
# ---------------------------------------------------------------------------


def test_get_finish_question_ref_gets_null_value_in_a_basic_case():
    strata: list = []
    res = get_finish_question_ref(strata)
    assert res == ""


def test_get_finish_question_ref_gets_the_ref_in_a_basic_case():
    strata = [
        {
            "audiences": [],
            "excluded_audiences": [],
            "metadata": {"gender": "men"},
            "creatives": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "foo"}],
                    },
                ],
            },
            "quota": 0.5,
            "id": "gender:men",
        }
    ]

    res = get_finish_question_ref(strata)
    assert res == "foo"


# ---------------------------------------------------------------------------
# describe('createStrataFromVariables with merge')
# ---------------------------------------------------------------------------


def test_merge_preserves_audiences_creatives_but_recomputes_quota_for_existing_stratum_ids():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        }
    ]

    existing_strata = [
        {
            "id": "gender:men",
            "quota": 0.3,
            "creatives": ["creative_A"],
            "audiences": ["audience_1"],
            "excluded_audiences": ["excluded_1"],
            "facebook_targeting": {"genders": [1]},
            "metadata": {"gender": "men"},
        }
    ]

    strata = create_strata_from_variables(variables, "foo", None, None, existing_strata)

    assert len(strata) == 2
    men_stratum = next(s for s in strata if s["id"] == "gender:men")
    # quota is derived from the variable levels, so a stale hand-edited 0.3 is
    # replaced by the current level quota rather than preserved.
    assert men_stratum["quota"] == 0.5
    assert men_stratum["creatives"] == ["creative_A"]
    assert men_stratum["audiences"] == ["audience_1"]
    assert men_stratum["excluded_audiences"] == ["excluded_1"]


def test_merge_drops_strata_whose_ids_no_longer_exist_in_the_new_combination_set():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                }
            ],
        }
    ]

    existing_strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": ["creative_A"],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "metadata": {"gender": "men"},
        },
        {
            "id": "gender:women",
            "quota": 0.5,
            "creatives": ["creative_A"],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [2]},
            "metadata": {"gender": "women"},
        },
    ]

    strata = create_strata_from_variables(variables, "foo", None, None, existing_strata)

    assert len(strata) == 1
    assert strata[0]["id"] == "gender:men"


def test_merge_adds_new_combinations_with_defaults():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        }
    ]

    existing_strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": ["creative_A"],
            "audiences": ["audience_1"],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "metadata": {"gender": "men"},
        }
    ]

    strata = create_strata_from_variables(variables, "foo", None, None, existing_strata)

    assert len(strata) == 2
    women_stratum = next((s for s in strata if s["id"] == "gender:women"), None)
    assert women_stratum is not None
    assert women_stratum["audiences"] == []
    assert women_stratum["creatives"] == []


# ---------------------------------------------------------------------------
# describe('strataStalenessHint')
# ---------------------------------------------------------------------------


def test_staleness_returns_true_when_a_level_is_added_to_a_variable():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": 0.5,
                },
            ],
        }
    ]

    saved_strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "finish_q"}],
                    },
                ],
            },
            "metadata": {"gender": "men"},
        }
    ]

    is_stale = strata_staleness_hint(variables, saved_strata)
    assert is_stale is True


def test_staleness_returns_false_when_nothing_changed():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                }
            ],
        }
    ]

    saved_strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "finish_q"}],
                    },
                ],
            },
            "metadata": {"gender": "men"},
        }
    ]

    is_stale = strata_staleness_hint(variables, saved_strata)
    assert is_stale is False


def test_staleness_returns_false_when_targeting_keys_are_in_different_order():
    variables = [
        {
            "name": "age",
            "properties": ["age_min", "age_max"],
            "levels": [
                {
                    "name": "18-34",
                    "template_campaign": "foo",
                    "template_adset": "18-34",
                    "facebook_targeting": {"age_min": 18, "age_max": 34},
                    "quota": 0.5,
                }
            ],
        }
    ]

    saved_strata = [
        {
            "id": "age:18-34",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"age_max": 34, "age_min": 18},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "18-34"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "finish_q"}],
                    },
                ],
            },
            "metadata": {"age": "18-34"},
        }
    ]

    is_stale = strata_staleness_hint(variables, saved_strata)
    assert is_stale is False


def test_staleness_returns_true_when_targeting_values_differ_for_the_same_stratum():
    variables = [
        {
            "name": "age",
            "properties": ["age_min", "age_max"],
            "levels": [
                {
                    "name": "18-34",
                    "template_campaign": "foo",
                    "template_adset": "18-34",
                    "facebook_targeting": {"age_min": 18, "age_max": 34},
                    "quota": 0.5,
                }
            ],
        }
    ]

    saved_strata = [
        {
            "id": "age:18-34",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"age_min": 25, "age_max": 34},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "age"},
                            {"type": "constant", "value": "18-34"},
                        ],
                    },
                    {
                        "op": "answered",
                        "vars": [{"type": "variable", "value": "finish_q"}],
                    },
                ],
            },
            "metadata": {"age": "18-34"},
        }
    ]

    is_stale = strata_staleness_hint(variables, saved_strata)
    assert is_stale is True


# ---------------------------------------------------------------------------
# describe('Regenerate propagates changed level quotas from Variables')
#
# Repro for the Girl Effect report (Jul 2026): quotas edited in Variables were
# not reflected in the Strata tab after clicking Regenerate.
# ---------------------------------------------------------------------------


def _gender_variables(men_quota: float, women_quota: float) -> list:
    return [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": men_quota,
                },
                {
                    "name": "women",
                    "template_campaign": "foo",
                    "template_adset": "women",
                    "facebook_targeting": {"genders": [2]},
                    "quota": women_quota,
                },
            ],
        }
    ]


def _question_targeting(level: str) -> dict:
    return {
        "op": "and",
        "vars": [
            {
                "op": "equal",
                "vars": [
                    {"type": "variable", "value": "gender"},
                    {"type": "constant", "value": level},
                ],
            },
            {"op": "answered", "vars": [{"type": "variable", "value": "foo"}]},
        ],
    }


# strata as previously saved by the study, generated from a 50/50 split
_SAVED_STRATA = [
    {
        "id": "gender:men",
        "quota": 0.5,
        "creatives": ["creative_A"],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {"genders": [1]},
        "metadata": {"gender": "men"},
        "question_targeting": _question_targeting("men"),
    },
    {
        "id": "gender:women",
        "quota": 0.5,
        "creatives": ["creative_A"],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {"genders": [2]},
        "metadata": {"gender": "women"},
        "question_targeting": _question_targeting("women"),
    },
]


def test_regenerate_recomputes_stratum_quotas_after_the_split_is_shifted_toward_men():
    strata = create_strata_from_variables(
        _gender_variables(0.7, 0.3), "foo", None, None, _SAVED_STRATA
    )

    assert next(s for s in strata if s["id"] == "gender:men")["quota"] == 0.7
    assert next(s for s in strata if s["id"] == "gender:women")["quota"] == 0.3


def test_regenerate_still_preserves_user_edited_creatives_while_recomputing_quota():
    strata = create_strata_from_variables(
        _gender_variables(0.7, 0.3),
        "foo",
        [{"name": "creative_B"}],
        None,
        _SAVED_STRATA,
    )

    assert next(s for s in strata if s["id"] == "gender:men")["creatives"] == [
        "creative_A"
    ]


def test_regenerate_flags_strata_as_stale_when_only_the_level_quotas_changed():
    assert strata_staleness_hint(_gender_variables(0.7, 0.3), _SAVED_STRATA) is True
    assert strata_staleness_hint(_gender_variables(0.5, 0.5), _SAVED_STRATA) is False


# ===========================================================================
# Beyond the spec: edge behaviour the TypeScript leaves implicit, pinned here
# because the port had to decide it one way or the other.
# ===========================================================================


def test_variable_with_zero_levels_yields_no_strata():
    # `a[0].map(...)` over an empty level list gives no combinations, so the
    # whole factorial is empty -- an incomplete variable produces nothing
    # rather than producing strata that ignore it.
    variables = [{"name": "gender", "properties": ["genders"], "levels": []}]

    assert create_strata_from_variables(variables, "foo") == []


def test_one_empty_variable_collapses_the_whole_product():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                }
            ],
        },
        {"name": "age", "properties": ["age_min"], "levels": []},
    ]

    assert create_strata_from_variables(variables, "foo") == []


def test_empty_finish_question_ref_is_treated_like_a_missing_one():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                }
            ],
        }
    ]

    assert create_strata_from_variables(variables, "") == []
    assert create_strata_from_variables(variables, None) == []


def test_audiences_become_excluded_audiences_by_default():
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.5,
                }
            ],
        }
    ]

    strata = create_strata_from_variables(
        variables,
        "foo",
        [{"name": "creative_A"}, {"name": "creative_B"}],
        [{"name": "aud_1", "subtype": "CUSTOM"}],
    )

    assert strata[0]["creatives"] == ["creative_A", "creative_B"]
    assert strata[0]["audiences"] == []
    assert strata[0]["excluded_audiences"] == ["aud_1"]


def test_later_levels_win_the_shallow_targeting_merge():
    # Two variables writing the same Facebook key do not combine; the later one
    # overwrites, exactly as JS object spread does.
    levels = [
        {
            "name": "wide",
            "facebook_targeting": {"age_min": 18, "age_max": 65},
            "quota": 0.5,
            "variable_name": "a",
        },
        {
            "name": "narrow",
            "facebook_targeting": {"age_min": 30},
            "quota": 0.5,
            "variable_name": "b",
        },
    ]

    stratum = format_group_product(levels, "finish")

    assert stratum["facebook_targeting"] == {"age_min": 30, "age_max": 65}
    assert stratum["id"] == "a:wide,b:narrow"
    assert stratum["quota"] == 0.25


def test_format_group_product_rejects_an_empty_level_list():
    # The TypeScript reduces `metadata` with no initial value and throws
    # `TypeError: Reduce of empty array with no initial value`; a clear
    # exception here keeps a nonsense stratum from being written.
    with pytest.raises(ValueError):
        format_group_product([], "finish")


def test_get_finish_question_ref_raises_without_an_answered_term():
    # The TypeScript throws a TypeError here (`finishFilter.vars` on
    # `undefined`). Raising deliberately rather than returning "" -- a wrong
    # ref would be silently stamped onto every regenerated stratum.
    strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "gender"},
                            {"type": "constant", "value": "men"},
                        ],
                    }
                ],
            },
            "metadata": {"gender": "men"},
        }
    ]

    with pytest.raises(ValueError):
        get_finish_question_ref(strata)


def test_staleness_propagates_the_missing_answered_term():
    # The TypeScript's `if (!finishRef) finishRef = "dummy"` fallback is dead
    # code -- `getFinishQuestionRef` throws before it can return a falsy ref
    # for a non-empty list. Ported faithfully: the error surfaces here too.
    saved_strata = [
        {
            "id": "gender:men",
            "quota": 0.5,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "metadata": {"gender": "men"},
        }
    ]

    with pytest.raises(ValueError):
        strata_staleness_hint(_gender_variables(0.5, 0.5), saved_strata)


def test_staleness_with_nothing_saved_yet():
    # Nothing saved and nothing designed: nothing to regenerate.
    assert strata_staleness_hint([], None) is False
    assert strata_staleness_hint([], []) is False
    # Variables designed but no strata saved: there is work to do, so the
    # banner shows -- this is the first Regenerate, not a stale one.
    assert strata_staleness_hint(_gender_variables(0.5, 0.5), None) is True
    assert strata_staleness_hint(_gender_variables(0.5, 0.5), []) is True
    # Every saved id vanishes when the variables do, so the lengths differ.
    assert strata_staleness_hint([], _SAVED_STRATA) is True


def test_quota_tolerance_absorbs_float_round_tripping():
    # 0.1 * 3 != 0.3 in binary floating point; the 1e-9 tolerance is what keeps
    # that from showing up as a permanent staleness banner.
    variables = [
        {
            "name": "gender",
            "properties": ["genders"],
            "levels": [
                {
                    "name": "men",
                    "template_campaign": "foo",
                    "template_adset": "men",
                    "facebook_targeting": {"genders": [1]},
                    "quota": 0.1 * 3,
                }
            ],
        }
    ]

    saved_strata = [
        {
            "id": "gender:men",
            "quota": 0.3,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"genders": [1]},
            "question_targeting": _question_targeting("men"),
            "metadata": {"gender": "men"},
        }
    ]

    assert 0.1 * 3 != 0.3
    assert strata_staleness_hint(variables, saved_strata) is False


class _Level(BaseModel):
    name: str
    template_campaign: str
    template_adset: str
    facebook_targeting: dict
    quota: float


class _Variable(BaseModel):
    name: str
    properties: list
    # Typed, so the level below is dumped by the *variable's* model_dump: the
    # test has to exercise a nested model, not a level pre-dumped by hand.
    levels: list[_Level]


def test_pydantic_models_are_accepted_as_input():
    # Callers holding a StudyConf shouldn't have to remember which shape these
    # functions want; they are dumped to the JSON wire shape on the way in.
    variables = [
        _Variable(
            name="gender",
            properties=["genders"],
            levels=[
                _Level(
                    name="men",
                    template_campaign="foo",
                    template_adset="men",
                    facebook_targeting={"genders": [1]},
                    quota=0.5,
                )
            ],
        )
    ]

    strata = create_strata_from_variables(variables, "foo")

    assert len(strata) == 1
    assert strata[0]["id"] == "gender:men"
    assert strata[0]["facebook_targeting"] == {"genders": [1]}


def _saved(stratum_id, quota_present=True, quota=0.5):
    stratum = {
        "id": stratum_id,
        "creatives": [],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {"age_min": 18},
        "question_targeting": {
            "op": "and",
            "vars": [
                {
                    "op": "answered",
                    "vars": [{"type": "variable", "value": "finish"}],
                }
            ],
        },
    }
    if quota_present:
        stratum["quota"] = quota
    return stratum


_ONE_LEVEL = [
    {
        "name": "a",
        "properties": [],
        "levels": [{"name": "a1", "facebook_targeting": {"age_min": 18}, "quota": 0.5}],
    }
]


def test_staleness_treats_a_null_saved_quota_as_zero_like_js():
    # `quota: null` is JSON-representable and JS coerces null to 0 in
    # arithmetic, so `fresh - null` is `fresh` and the stratum is stale. This
    # is a different case from a *missing* quota (below). The first cut of the
    # port used `.get("quota") is None` for both and answered False here; the
    # fixtures never emit a null quota, so only review caught it.
    saved = [_saved("a:a1", quota=None)]
    assert strata_staleness_hint(_ONE_LEVEL, saved) is True


def test_staleness_ignores_a_missing_saved_quota_like_js():
    # Missing key: JS reads `undefined`, the subtraction is NaN, and
    # `NaN > 1e-9` is false. Not stale.
    saved = [_saved("a:a1", quota_present=False)]
    assert strata_staleness_hint(_ONE_LEVEL, saved) is False


@pytest.mark.parametrize(
    "name, expected",
    [
        (18, "18"),
        (1.0, "1"),
        (1.5, "1.5"),
        (True, "true"),
        (False, "false"),
        (None, "null"),
    ],
)
def test_stratum_id_interpolates_non_string_level_names_like_js(name, expected):
    # The id is the merge key against saved strata and what the dashboard
    # reads back, so it has to be byte-identical to the TypeScript's
    # `${variableName}:${name}`. Level names are strings when they come off
    # the dashboard; these arrive from YAML- or notebook-authored variables.
    variables = [
        {
            "name": "age",
            "properties": [],
            "levels": [{"name": name, "facebook_targeting": {}, "quota": 1}],
        }
    ]
    strata = create_strata_from_variables(variables, "finish")
    assert strata[0]["id"] == f"age:{expected}"


def test_get_finish_question_ref_raises_for_an_empty_first_stratum():
    # JS `!{}` is false, so the TypeScript reaches `s.question_targeting.vars`
    # and throws. Returning "" here instead would stamp an empty ref onto
    # every regenerated stratum.
    with pytest.raises(ValueError):
        get_finish_question_ref([{}])
