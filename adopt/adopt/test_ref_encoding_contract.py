"""vlab's half of the encoded-ref deploy contract.

The other half is fly's `replybot/lib/typewheels/ref-encoding-contract.test.js`,
which loads the replybot tag named by fly's `devops/values/production.yaml` and
decodes these same vectors with it.

WHY THE CONTRACT IS TWO HALVES AND NOT ONE TEST
-----------------------------------------------
`ref_encoding.decode_recruitment_ref` is a **reimplementation** of fly's
decoder, and `test_marketing.WHATSAPP_ENTRY_REF` is a **verbatim copy** of
fly's entry pattern. Both are vendored across a repository boundary and a
language boundary, and until this file existed nothing detected drift in
either. Two drifts had in fact accumulated by 2026-08-26, both found by writing
this:

  1. the vendored `WHATSAPP_ENTRY_REF` sat at replybot-v0.0.219's shape while
     v0.0.221 ran -- v0.0.220 had widened it to let the `form` pair appear
     anywhere in the pair list.

  2. `documentation/ad-attributions.md` recorded, as verified, that
     `make_ref`'s output "can never match" that pattern. The same widening made
     it always match.

Neither is a runtime bug -- vlab still emits form-first and fly still reads it
-- but both were load-bearing claims that had quietly stopped being true.

WHY THE FIXTURE, AND WHY IT IS DUPLICATED
------------------------------------------
`ref_encoding_vectors.json` sits beside `ref_encoding.py`, which is what mints
these strings, and a byte-identical copy sits in fly. Duplicated on purpose:
neither repo needs the other checked out to run its half, which is what makes
this a check either side can run in CI rather than a manual cross-repo ritual
that gets skipped.

The duplication is held closed by a digest. Both copies carry a sha256 over
their own vectors, both halves recompute it, and both compare it to a constant
hardcoded in the test file. Editing a vector fails the self-check; editing the
vector and the digest together fails the constant. The file is the v1 wire
format and every ad ever published carries exactly these bytes -- a format
change is a new version, never an edit.
"""

import hashlib
import json
from pathlib import Path

import pytest

from .ref_encoding import decode_recruitment_ref, encode_recruitment_ref
from .test_marketing import _fly_would_accept

FIXTURE_PATH = Path(__file__).with_name("ref_encoding_vectors.json")
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
VECTORS = FIXTURE["vectors"]

# The same constant appears in fly's ref-encoding-contract.test.js. Two
# independent copies of one number is the point: it is the one value that must
# be changed in both repositories at once, so a change cannot be half-made.
EXPECTED_DIGEST = "86d3374214a993346ee9f83390597be3d1d757e441c0380b5f166c3cbeb082e6"


def _canonical(vectors) -> str:
    """The serialisation both repos hash.

    `ensure_ascii=False` matters: two vectors carry non-ASCII shortcodes, and
    escaping them would hash differently from fly's JSON.stringify, which does
    not escape. `sort_keys` and the tight separators remove every other degree
    of freedom.
    """
    return json.dumps(vectors, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


# --- the fixture is frozen -------------------------------------------------


def test_the_fixture_has_not_been_edited():
    digest = hashlib.sha256(_canonical(VECTORS).encode("utf-8")).hexdigest()

    assert digest == FIXTURE["digest"], (
        "a vector changed but the fixture's own digest did not"
    )
    assert digest == EXPECTED_DIGEST, (
        "the fixture changed. It is the v1 wire format and every ad already "
        "published carries exactly these bytes -- a format change is a new "
        "version and a new file, not an edit to this one. If you are genuinely "
        "adding a v1 vector, update this constant AND fly's copy of it in the "
        "same change."
    )


def test_the_fixture_is_version_one():
    assert FIXTURE["format_version"] == 1


# --- vlab MINTS what fly decodes -------------------------------------------


@pytest.mark.parametrize("v", VECTORS["mint"], ids=lambda v: v["why"][:60])
def test_vlab_mints_the_contract_bytes(v):
    """The producer half. fly asserts its deployed tag consumes these."""
    assert encode_recruitment_ref(v["shortcode"], v["token"]) == v["encoded"]
    assert v["ref"] == f"r.{v['encoded']}"


@pytest.mark.parametrize("v", VECTORS["mint"], ids=lambda v: v["why"][:60])
def test_vlabs_own_decoder_round_trips_them(v):
    """The mirror decoder agrees with the encoder.

    Not redundant with fly's half. This catches an encoder/decoder pair that
    drifted together into a private format -- which would still round-trip
    here and would be decoded wrongly, or not at all, by the thing that
    actually matters.
    """
    assert decode_recruitment_ref(v["encoded"]) == (v["shortcode"], v["token"])


@pytest.mark.parametrize("v", VECTORS["reject"], ids=lambda v: v["why"][:60])
def test_vlabs_decoder_refuses_what_a_v1_decoder_must_refuse(v):
    """The half with teeth.

    A decoder returning a constant would satisfy every positive vector above
    when they are checked one at a time. Only these make it prove it
    discriminates -- and `encode_recruitment_ref` cannot produce any of them,
    so they exist only as literals.
    """
    with pytest.raises(ValueError):
        decode_recruitment_ref(v["encoded"])


# --- the vendored WhatsApp gate agrees with the deployed one ---------------
#
# `_fly_would_accept` is imported from `test_marketing` rather than
# reimplemented here, deliberately: the copy under test has to be the copy the
# other tests actually rely on. A second copy checked against the fixture would
# pass while the one doing the work stayed stale -- which is the exact shape of
# the bug this file was written to catch.


@pytest.mark.parametrize("v", VECTORS["whatsapp_entry_accept"],
                         ids=lambda v: v["body"][:40])
def test_the_vendored_gate_accepts_what_the_deployed_gate_accepts(v):
    assert _fly_would_accept(v["body"]), (
        f"the deployed replybot accepts {v['body']!r} and the vendored copy of "
        "its pattern does not. The copy is stale -- re-diff it against "
        "replybot/lib/event-normalizer.js at the tag in fly's "
        "devops/values/production.yaml."
    )


@pytest.mark.parametrize("v", VECTORS["whatsapp_entry_reject"],
                         ids=lambda v: v["body"][:40])
def test_the_vendored_gate_rejects_what_the_deployed_gate_rejects(v):
    assert not _fly_would_accept(v["body"]), (
        f"the vendored copy accepts {v['body']!r} and the deployed replybot "
        "does not. This direction is the dangerous one: adopt would publish a "
        "ref that fly refuses, and the respondent lands in FALLBACK_FORM -- a "
        "real survey, so they look like a completion rather than an error."
    )


@pytest.mark.parametrize("v", VECTORS["whatsapp_entry_throws"],
                         ids=lambda v: v["body"][:40])
def test_a_body_the_gate_admits_but_the_decoder_refuses(v):
    """The gate cannot validate a payload, and is not supposed to.

    Its alphabet is `[A-Za-z0-9_-]`, which every corrupt base64url string also
    satisfies. So the gate lets `r.AAAA` through and the DECODER is what
    refuses it -- loudly, because the encoded ref is the only carrier of the
    shortcode and a silent failure would be a FALLBACK_FORM misroute.

    Asserted from both sides here: the vendored gate admits it, and vlab's
    mirror decoder rejects it. fly's half asserts the same body throws out of
    `getMetadata` on the deployed tag.
    """
    body = v["body"].strip().removeprefix("start ")
    assert _fly_would_accept(body)

    with pytest.raises(ValueError):
        decode_recruitment_ref(body.removeprefix("r."))
