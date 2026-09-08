"""Guards on the field contract itself, as opposed to how _eq consumes it.

The declarations in field_contract are the load-bearing part: an entry missing
from DROPPED is a rewrite loop (VIR-49, planning/field-contract.md), and an
entry whose path is subtly wrong is the same thing wearing a disguise, because
nothing else in the system would notice.
"""

import re

from . import field_contract
from .probe import BEGIN, CONTRACT_PATH, END, render_dropped_block

BLURBS = "degrees_of_freedom_spec.creative_features_spec.show_destination_blurbs"


def test_show_destination_blurbs_is_declared_dropped():
    # VIR-49: undeclared, this rewrote all 12 ads of the LAC Bolivia campaign
    # on every two-hourly run — 144 no-op ad writes a day, each minting a new
    # creative, on the same ad account that hit `code 17` in July.
    assert field_contract.is_dropped(BLURBS)


def test_is_dropped_accepts_the_path_shape_eq_actually_builds():
    # _eq composes paths with a leading dot. A declaration that only matches
    # the undotted form is silently inert, which looks exactly like not having
    # declared it at all.
    assert field_contract.is_dropped(f".{BLURBS}")


def test_dropped_paths_are_rooted_in_a_compared_field():
    # DROPPED only ever suppresses a difference underneath a COMPARED_* field.
    # A path rooted anywhere else is dead weight that reads as protection.
    roots = set(field_contract.COMPARED_AD) | set(field_contract.COMPARED_ADSET)

    for path in field_contract.DROPPED:
        assert path.split(".")[0] in roots, f"{path} is not under a compared field"


def test_every_declaration_says_when_it_was_confirmed():
    # A drop is a claim about Meta's behaviour at a point in time. Without a
    # date there is no way to know whether it is still true.
    for path, why in field_contract.DROPPED.items():
        assert re.search(r"\d{4}-\d{2}-\d{2}", why), f"{path} has no confirmation date"


def test_committed_block_is_what_adopt_probe_would_write():
    # The block is machine-managed but hand-editable, so the two must agree.
    # If they drift, the next `--update` reflows every entry and buries the
    # one line that actually changed in a whole-block diff.
    committed = re.search(
        re.escape(BEGIN) + r".*?" + re.escape(END),
        CONTRACT_PATH.read_text(),
        re.DOTALL,
    )

    assert committed is not None
    assert committed.group(0) == render_dropped_block(field_contract.DROPPED)
