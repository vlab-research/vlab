"""Tests for `authoring/sheets.py`, the salvaged spreadsheet readers.

`read_share_lookup`'s five cases are `test_configuration.py`'s, moved
verbatim -- the point of a salvage is that behaviour does not change, and the
workbook they read (`test/targeting_distribution_test_sheet.xlsx`) is the same
file. `test_configuration.py` keeps its copies too, pinning the old home until
somebody deletes it.

The `parse_*_sheet` tests are new. There were none: the notebook-era workbooks
in `test/` were written against models that have since dropped fields
(`general` still carries `objective` and `page_id`; `creative` still carries
`image_hash` and `body`), so they cannot be parsed into today's models at all.
That is itself worth a test, because it is the failure a researcher opening an
old workbook will hit. Everything else builds its own workbook in `tmp_path`.
"""

from typing import Dict, List, NamedTuple, Optional

import numpy as np
import pandas as pd
import pytest

from ..study_conf import CreativeConf, GeneralConf
from .sheets import SheetError, parse_kv_sheet, parse_row_sheet, read_share_lookup

SHARE_SHEET = "test/targeting_distribution_test_sheet.xlsx"


# ---------------------------------------------------------------------------
# read_share_lookup -- moved from test_configuration.py, unchanged
# ---------------------------------------------------------------------------


def test_read_share_lookup_works_with_one_variable():
    share_lookup = read_share_lookup(
        SHARE_SHEET, ["location"], "targeting_distribution_single"
    )

    expect = pd.DataFrame(
        [("West", 0.6), ("East", 0.4)], columns=["location", "percentage"]
    )

    assert expect.equals(share_lookup)


def test_read_share_lookup_works_with_two_variables():
    share_lookup = read_share_lookup(
        SHARE_SHEET, ["location", "gender"], "targeting_distribution_double"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", 0.3),
            ("East", "1", 0.2),
            ("West", "2", 0.1),
            ("East", "2", 0.4),
        ],
        columns=["location", "gender", "percentage"],
    )

    assert expect.equals(share_lookup)


def test_read_share_lookup_works_with_three_variables():
    share_lookup = read_share_lookup(
        SHARE_SHEET, ["location", "gender", "age"], "targeting_distribution_triple"
    )

    expect = pd.DataFrame(
        [
            ("West", "1", "18", 0.12),
            ("East", "1", "18", 0.08),
            ("West", "2", "18", 0.04),
            ("East", "2", "18", 0.16),
            ("West", "1", "40", 0.18),
            ("East", "1", "40", 0.12),
            ("West", "2", "40", 0.06),
            ("East", "2", "40", 0.24),
        ],
        columns=["location", "gender", "age", "percentage"],
    )

    assert expect[["location", "gender", "age"]].equals(
        share_lookup[["location", "gender", "age"]]
    )
    assert np.allclose(share_lookup.percentage.values, expect.percentage.values)


def test_read_share_lookup_works_with_four_variables():
    share_lookup = read_share_lookup(
        SHARE_SHEET,
        ["location", "gender", "age", "education"],
        "targeting_distribution_four",
    )

    assert list(share_lookup.columns) == [
        "location",
        "gender",
        "age",
        "education",
        "percentage",
    ]
    assert len(share_lookup) == 16
    assert np.isclose(share_lookup.percentage.sum(), 2.0)


def test_read_share_lookup_works_with_four_variables_and_one_location():
    share_lookup = read_share_lookup(
        SHARE_SHEET,
        ["location", "gender", "age", "education"],
        "targeting_distribution_four_1",
    )

    assert set(share_lookup.location.unique()) == {"West"}
    assert len(share_lookup) == 8


def test_level_values_come_back_as_strings():
    """So they can be joined against level names, which are strings everywhere.

    `gender` is 1 and 2 in the workbook and "1" and "2" here.
    """
    share = read_share_lookup(
        SHARE_SHEET, ["location", "gender"], "targeting_distribution_double"
    )
    assert set(share.gender) == {"1", "2"}


# ---------------------------------------------------------------------------
# parse_kv_sheet / parse_row_sheet
# ---------------------------------------------------------------------------


class _Targeting(NamedTuple):
    """A NamedTuple target, as the notebooks' `TargetingConf` was."""

    template_campaign_name: Optional[str]
    distribution_vars: List[str]


def _write(path, sheets: Dict[str, pd.DataFrame]) -> str:
    with pd.ExcelWriter(path) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return str(path)


def _kv(pairs, note_column=True) -> pd.DataFrame:
    data = {"key": [k for k, _ in pairs], "value": [v for _, v in pairs]}
    if note_column:
        # Every real workbook carries a third, human-readable hint column. It
        # must be ignored rather than parsed.
        data["notes"] = ["a note"] * len(pairs)
    return pd.DataFrame(data)


def test_parse_kv_sheet_builds_a_pydantic_conf(tmp_path):
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "general": _kv(
                [
                    ("name", "hpv-nigeria"),
                    ("credentials_key", "Facebook"),
                    ("credentials_entity", "facebook"),
                    ("ad_account", "1342820622846299"),
                    ("opt_window", "48"),
                    ("extra_metadata", '{"wave": "1"}'),
                ]
            )
        },
    )

    conf = parse_kv_sheet(path, "general", GeneralConf)

    assert isinstance(conf, GeneralConf)
    assert conf.name == "hpv-nigeria"
    assert conf.opt_window == 48  # a string cell, cast by the int annotation
    assert conf.extra_metadata == {"wave": "1"}  # a string cell, json.loads'd


def test_a_comma_separated_cell_becomes_a_list(tmp_path):
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "targeting": _kv(
                [
                    ("template_campaign_name", "template"),
                    ("distribution_vars", "location, gender, age"),
                ]
            )
        },
    )

    conf = parse_kv_sheet(path, "targeting", _Targeting)

    assert conf.distribution_vars == ["location", "gender", "age"]


def test_an_empty_cell_becomes_none_not_nan(tmp_path):
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "targeting": _kv(
                [("template_campaign_name", None), ("distribution_vars", "location")]
            )
        },
    )

    conf = parse_kv_sheet(path, "targeting", _Targeting)

    assert conf.template_campaign_name is None


def test_a_column_the_model_does_not_have_names_itself(tmp_path):
    """The likeliest failure when opening an old workbook: `GeneralConf`
    dropped `objective` and `page_id`, which every notebook-era `general` tab
    still carries. The ancestor raised a bare KeyError here."""
    path = _write(
        tmp_path / "conf.xlsx",
        {"general": _kv([("name", "x"), ("page_id", "1855355231229529")])},
    )

    with pytest.raises(SheetError) as e:
        parse_kv_sheet(path, "general", GeneralConf)

    assert "page_id" in str(e.value)
    assert "credentials_key" in str(e.value)  # the message lists what IS accepted


def test_a_tab_with_no_value_column_says_so(tmp_path):
    path = _write(
        tmp_path / "conf.xlsx",
        {"general": pd.DataFrame({"key": ["name"], "not_value": ["x"]})},
    )

    with pytest.raises(SheetError) as e:
        parse_kv_sheet(path, "general", GeneralConf)

    assert "value" in str(e.value)


def test_parse_row_sheet_builds_a_list_of_confs(tmp_path):
    """The one shape all seventeen notebooks used: a `creative` tab."""
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "creative": pd.DataFrame(
                [
                    {
                        "name": "banner-99",
                        "destination": "fly",
                        "template": '{"actor_id": "1"}',
                        "tags": None,
                    },
                    {
                        "name": "amazon-girl",
                        "destination": "fly",
                        "template": '{"actor_id": "1"}',
                        "tags": None,
                    },
                ]
            )
        },
    )

    creatives = parse_row_sheet(path, "creative", CreativeConf)

    assert [c.name for c in creatives] == ["banner-99", "amazon-girl"]
    assert creatives[0].template == {"actor_id": "1"}
    assert creatives[0].tags is None


def test_a_bad_cell_names_the_cell(tmp_path):
    """The reason the reader constructs the model rather than returning dicts:
    the failure arrives here, with the field name, instead of as a 422 from a
    POST or a KeyError in a cron hours later.

    The ancestor raised `ValueError: invalid literal for int() with base 10:
    'not-a-number'`, which does not say which of a workbook's forty cells it
    came from.
    """
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "general": _kv(
                [
                    ("name", "x"),
                    ("credentials_key", "Facebook"),
                    ("credentials_entity", "facebook"),
                    ("ad_account", "123"),
                    ("opt_window", "not-a-number"),
                ]
            )
        },
    )

    with pytest.raises(SheetError) as e:
        parse_kv_sheet(path, "general", GeneralConf)

    assert "opt_window" in str(e.value)
    assert "not-a-number" in str(e.value)


def test_a_malformed_json_cell_names_the_cell_too(tmp_path):
    path = _write(
        tmp_path / "conf.xlsx",
        {
            "general": _kv(
                [
                    ("name", "x"),
                    ("credentials_key", "Facebook"),
                    ("credentials_entity", "facebook"),
                    ("ad_account", "123"),
                    ("opt_window", "48"),
                    ("extra_metadata", "{not json}"),
                ]
            )
        },
    )

    with pytest.raises(SheetError) as e:
        parse_kv_sheet(path, "general", GeneralConf)

    assert "extra_metadata" in str(e.value)
