"""Spreadsheet readers: a workbook tab becomes a conf, or a quota table.

Salvaged from `adopt/configuration.py` (superseded) -- the three readers a
read-through of `~/Documents/vlab-research/campaigns/*.ipynb` found were
actually used, and used constantly: `parse_kv_sheet` in 68 call sites across 17
notebooks, `parse_row_sheet` in 17, `read_share_lookup` in 17. What was dropped,
and why, is in `planning/vlab-sdk.md`; the short version is that everything
dropped either had zero notebook callers or was superseded by
`adopt.authoring.strata` and the Meta proxy.

WHY A SPREADSHEET READER IS IN AN AUTHORING LIBRARY AT ALL

Because the quota split of a real study is a demographic table, and a
demographic table arrives as a spreadsheet. `read_share_lookup` turns the
census tab a researcher was handed into the per-level quotas the strata
compiler multiplies. The dashboard has no equivalent and cannot have one; this
is the "fancy combination" plan §6.D refuses to foreclose.

`parse_kv_sheet` and `parse_row_sheet` are the other half: a key/value tab
becomes a `GeneralConf`, a row-per-record tab becomes `list[CreativeConf]`.
Both take the pydantic model as an argument and construct it, so a bad cell is
a pydantic error naming the field rather than a 422 hours later.

THE PART THAT IS NOT GOOD, MARKED RATHER THAN QUIETLY SHIPPED

`read_share_lookup`'s multi-level branch is unstack/reorder_levels pandas that
the original module's own comment called "crazy pandas magic. Probably worth
redoing from scratch". It is moved here unchanged, because the five tests in
`test_sheets.py` pin its exact output against a real workbook and a rewrite
would be a behaviour change dressed as a move. But four of the seventeen
notebooks that used it shadowed it with their own rewrite immediately before
calling it, which is the corpus saying it does not always do what people want.
Treat it as working-for-the-shapes-it-is-tested-on, not as general.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Type, TypeVar, get_type_hints

import pandas as pd

__all__ = [
    "SheetError",
    "parse_kv_sheet",
    "parse_row_sheet",
    "read_share_lookup",
]

T = TypeVar("T")


class SheetError(Exception):
    """A cell or a column the target model cannot accept."""


# ---------------------------------------------------------------------------
# Key/value and row tabs -> pydantic confs
# ---------------------------------------------------------------------------


def parse_kv_sheet(path: str, sheet_name: str, type_: Type[T]) -> T:
    """A two-column `key`/`value` tab, as one instance of `type_`.

    The layout is the notebook convention and is unchanged: the first column is
    the index (field names), and a column literally called `value` holds the
    values. Any further columns -- the workbooks in `test/` carry a
    human-readable "Text field" hint column -- are ignored.

    `type_` is anything constructible from keyword arguments whose annotations
    `typing.get_type_hints` can read: the pydantic models in
    `adopt.study_conf` (which is what every real caller passed) and plain
    NamedTuples both work.
    """
    df = pd.read_excel(path, sheet_name=sheet_name, index_col=[0])
    try:
        values = {k: v["value"] for k, v in df.to_dict(orient="index").items()}
    except KeyError:
        raise SheetError(
            f"Sheet {sheet_name!r} in {path} has no 'value' column; a key/value "
            f"tab needs the field name in the first column and a column called "
            f"'value'. Found: {list(df.columns)}"
        )

    return type_(**_cast_strings(type_, values))


def parse_row_sheet(path: str, sheet_name: str, type_: Type[T]) -> List[T]:
    """A tab with one record per row, as a list of `type_`.

    The header row supplies the field names, so the tab's columns must be
    exactly the model's fields -- this is what a `creative` tab is, and
    `list[CreativeConf]` is what it was always turned into.
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    return [type_(**_cast_strings(type_, row)) for row in df.to_dict(orient="records")]


def _cast_strings(type_: Type[Any], values: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce Excel's cell values towards what the model's annotations want.

    Excel gives back strings, floats and `NaN`; the models want lists, dicts,
    ints and `None`. The four rules, all inherited unchanged because real
    workbooks depend on every one of them:

    * `NaN` (an empty cell) becomes `None`, so an optional field left blank is
      absent rather than a float nobody can use;
    * a string for a `list`-annotated field is split on commas and stripped, so
      `location, gender, age` in one cell is three values;
    * a string for a `dict`-annotated field is `json.loads`'d, which is how
      `extra_metadata` and `facebook_targeting` fit in a cell;
    * a string for `int`/`float`/`str`/`bool` is passed through that
      constructor. Note `bool("false") is True` -- inherited, and a trap: write
      an empty cell rather than the word "false".

    Anything else is left alone for the model to validate, which for a pydantic
    target is strictly better than guessing here.
    """
    out = dict(values)
    hints = get_type_hints(type_)

    for key, value in values.items():
        if key not in hints:
            # The ancestor raised a bare `KeyError` here, which reads as an
            # internal error rather than "your spreadsheet has a column this
            # model does not have". That is the likeliest failure when opening
            # an old workbook against current models -- `test/example_ads_conf_fly.xlsx`'s
            # `general` tab still carries `objective` and `page_id`, which
            # `GeneralConf` dropped -- so it gets a message that says so.
            raise SheetError(
                f"{type_.__name__} has no field {key!r}. Fields: {sorted(hints)}"
            )

        if _is_missing(value):
            out[key] = None
            continue

        if not isinstance(value, str):
            continue

        hint = hints[key]
        origin = getattr(hint, "__origin__", None)

        if origin in (list, List):
            out[key] = [x.strip() for x in value.split(",")]
        elif origin in (dict, Dict):
            out[key] = _try(key, value, json.loads, "valid JSON")
        elif hint in (int, float, str, bool):
            out[key] = _try(key, value, hint, hint.__name__)

    return out


def _try(key: str, value: str, cast: Any, wanted: str) -> Any:
    """Cast a cell, and name the cell when it will not cast.

    The ancestor called `int(value)` bare, so a typo'd number surfaced as
    `ValueError: invalid literal for int() with base 10: 'not-a-number'` --
    which says nothing about which of a workbook's forty cells it came from.
    Naming the field is the entire reason a reader is better than
    `pd.read_excel` plus a dict comprehension, so this is not cosmetic.
    """
    try:
        return cast(value)
    except (TypeError, ValueError) as e:
        raise SheetError(f"Cell {key!r} holds {value!r}, which is not {wanted}.") from e


def _is_missing(value: Any) -> bool:
    """`pd.isna`, guarded.

    `pd.isna` on a list or an array returns an array, and putting that in an
    `if` raises. Cells cannot hold lists, but `parse_row_sheet` is public and a
    caller can hand it anything.
    """
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# The share lookup
# ---------------------------------------------------------------------------


def read_share_lookup(
    path: str, distribution_vars: Sequence[str], tab_name: str
) -> pd.DataFrame:
    """A quota table, as a long DataFrame of `[*distribution_vars, percentage]`.

    One variable: a flat two-column tab. Two or more: a cross-tab, with the
    first variable down the side and the rest across the top as a multi-level
    header, which is how a census table is actually laid out and why this is
    not just `read_excel`.

    Every level value is stringified, so `gender` 1 and 2 come back as `"1"`
    and `"2"` and can be joined against level names, which are strings
    everywhere else in the system.

    Caveat, from the module docstring: the multi-level branch is inherited
    pandas that four of its seventeen notebook callers replaced with their own.
    Check the output before trusting it on a new tab shape.
    """
    if len(distribution_vars) == 1:
        return _read_single_value_share_lookup(path, distribution_vars[0], tab_name)

    if len(distribution_vars) == 2:
        # 2 levels needs some level dropping. Who knows why. (Inherited comment,
        # inherited behaviour: a two-variable tab's second header row is a
        # repeated label pandas keeps and nothing wants.)
        df = pd.read_excel(path, header=[0, 1], index_col=0, sheet_name=tab_name)
        df = df.dropna(axis=1)
        df.columns = df.columns.droplevel(1)
    else:
        header = list(range(0, len(distribution_vars) - 1))
        df = pd.read_excel(path, header=header, index_col=0, sheet_name=tab_name)
        df = df.dropna(axis=1)

    df.index.rename(distribution_vars[0], inplace=True)
    df = df.unstack()
    df.index = df.index.reorder_levels(list(distribution_vars))
    df.index = pd.MultiIndex.from_tuples(
        [tuple(str(v) for v in t) for t in df.index], names=df.index.names
    )

    return df.reset_index(name="percentage")


def _read_single_value_share_lookup(
    path: str, var_name: str, tab_name: str
) -> pd.DataFrame:
    """The one-variable branch. Private: no notebook ever called it by name.

    Kept as its own function rather than inlined only because the two branches
    read nothing alike and the caller above is clearer for the split.
    """
    df = pd.read_excel(path, sheet_name=tab_name)
    df = df.dropna(axis=1)
    df.columns = [var_name, "percentage"]
    return df
