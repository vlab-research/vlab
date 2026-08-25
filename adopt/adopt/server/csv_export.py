"""CSV rendering for the ad -> stratum mapping.

Pure functions over already-fetched rows; no database, no HTTP. The point of
this export is one sentence for the researcher:

    left-join your fly export on `ad_id` and you get your old metadata columns
    back, under the same names.

For a study using the encoded ref, the join column is `ref_token` instead --
fly exposes it as the response metadata key `vt`. Same sentence, different key,
and which one applies is fixed by the study's ref mode rather than chosen per
row. Both columns are always present; the one that does not apply is empty.

That is only true because the frozen metadata blob is key-for-key the dict the
dotted ref used to carry (see documentation/ad-attributions.md, invariant 1).
The blob's keys therefore become the CSV's columns verbatim, rather than being
renamed or nested.
"""

import csv
import io
from typing import Any, Dict, List, Sequence

# Columns that come from the row itself rather than from the frozen blob.
# `created` trails the metadata so the ad's own identity leads and the
# researcher's familiar column names sit together in the middle.
# `ref_token` sits with the ad's identity because that is what it is: the other
# key a respondent can arrive carrying. Empty for every ad whose destination is
# not in ref_mode "encoded", which is most of them.
LEADING_COLUMNS = ["ad_id", "network", "ref_token"]
TRAILING_COLUMNS = ["created"]
RESERVED_COLUMNS = set(LEADING_COLUMNS) | set(TRAILING_COLUMNS)


def metadata_columns(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """The metadata keys to emit, in a stable order.

    Keys are uniform within a study in practice, but a study whose stratum conf
    changed mid-flight has rows frozen under both shapes — and the append-only
    rule means both survive. So this takes the union rather than trusting the
    first row, in first-seen order so the output is deterministic.
    """
    columns: List[str] = []
    seen = set()

    for row in rows:
        for key in row.get("metadata") or {}:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    return columns


def column_name(key: str) -> str:
    """The header a metadata key is written under.

    Metadata keys are the researcher's own stratum vocabulary and normally pass
    through untouched — that is the whole join story. The one exception is a key
    that collides with a row column, which would otherwise produce two columns
    of the same name and silently confuse whatever reads the file. Vanishingly
    rare, but a duplicate header is the kind of thing nobody notices until the
    analysis is wrong.
    """
    return f"metadata_{key}" if key in RESERVED_COLUMNS else key


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def headers(md_keys: Sequence[str]) -> List[str]:
    """The column list, in order."""
    return LEADING_COLUMNS + [column_name(k) for k in md_keys] + TRAILING_COLUMNS


def cells(row: Dict[str, Any], md_keys: Sequence[str]) -> List[str]:
    """One row's values, in the order `headers` names them."""
    md = row.get("metadata") or {}

    return (
        [_cell(row.get(c)) for c in LEADING_COLUMNS]
        + [_cell(md.get(k)) for k in md_keys]
        + [_cell(row.get(c)) for c in TRAILING_COLUMNS]
    )


def ad_attributions_csv(rows: Sequence[Dict[str, Any]]) -> str:
    """Render mapping rows as a CSV file, positionally.

    Every row is emitted, including rows whose ad Facebook no longer has.
    Reconciliation deletes ads that fall out of the desired set, but respondents
    keep arriving from deleted ads through reshared page posts — so a CSV of
    only live ads would silently lack rows the researcher needs to join against,
    and the missing rows would look like unattributed respondents.
    """
    md_keys = metadata_columns(rows)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers(md_keys))

    for row in rows:
        writer.writerow(cells(row, md_keys))

    return out.getvalue()


def ad_attributions_table(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The same rendering as a table, for the dashboard.

    Columns and cells come from `headers` and `cells`, the same definition the
    file is written from. The columns are a union across rows in first-seen
    order, so a table deriving them separately would show a different shape from
    the file downloaded seconds later.
    """
    md_keys = metadata_columns(rows)
    columns = headers(md_keys)

    return {
        "columns": columns,
        "rows": [dict(zip(columns, cells(row, md_keys))) for row in rows],
    }
