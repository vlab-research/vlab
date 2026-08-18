"""The encoded recruitment ref: one opaque string carrying route *and* join key.

CROSS-REPO CONTRACT. The decoder is `decodeRecruitmentRef` in
fly@replybot/lib/typewheels/utils.js and the byte layout below is pinned by
tests on both sides. Changing it means changing both repos together, and
bumping ENCODED_REF_VERSION so an old fly rejects a new ref loudly instead of
mis-parsing it.

The wire format, base64url (unpadded) of:

    byte 0      version, currently 0x01
    byte 1      length of the shortcode IN BYTES, 1..255
    bytes 2..   the shortcode, UTF-8
    remainder   the opaque token, >= 1 byte, surfaced as lowercase hex

Why this shape rather than the alternatives:

  - **base64url, not the dotted grammar.** The alphabet is `[A-Za-z0-9_-]`,
    which contains no `.`, so an encoded ref cannot collide with the dotted
    key/value grammar `make_ref` emits and cannot be mis-paired by fly's
    `_group`. It also passes fly's WhatsApp entry gate unencoded, which the
    dotted form only manages via percent-escapes.

  - **Length-prefixed, not delimited.** A shortcode is researcher-chosen text.
    Any delimiter is a character a shortcode might one day contain, and the
    failure would be a silent mis-route -- the exact class of bug this whole
    design exists to remove. A byte count cannot be spoofed by content.

  - **Length in bytes, not characters.** UTF-8 is variable width, and slicing a
    buffer by character count silently truncates a multi-byte shortcode.

  - **The shortcode travels in the clear (base64 is not encryption).** That is
    fine and deliberate: routing is the one thing fly cannot defer, so the ref
    must be self-describing. What the ref no longer ships is the study's
    *stratum vocabulary* -- that stays behind the opaque token.

The token is a join key into `ad_attributions`, not a lookup id fly resolves.
fly decodes locally and synchronously, because routing happens on the first
inbound message; attribution is a batch join done afterwards, in vlab.
"""

import hashlib
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from typing import NamedTuple

# Bumped only when the byte layout changes, and only in lockstep with fly.
ENCODED_REF_VERSION = 1

# 40 bits. Sized against what actually has to be unique: the (stratum,
# creative, destination) triples of ONE study, which is hundreds, not millions
# -- collisions across studies are harmless because every lookup is per-study
# (see ad-attributions.md, "The load is per study"). At 1,000 triples the
# birthday probability is ~5e-7, and `assert_ref_tokens_unique` turns even that
# into a loud config error rather than a silent mis-join.
#
# Five bytes also keeps the whole ref short: an 8-char shortcode encodes to 20
# base64url characters, which matters because the WhatsApp arm's ref sits in
# the respondent's compose box where they can see it.
REF_TOKEN_BYTES = 5

# Domain separation. Without it the digest is just "a hash of some strings",
# and any other feature that hashes the same tuple would produce colliding
# tokens for unrelated things.
_TOKEN_DOMAIN = b"vlab.ref-token.v1"

# A byte that cannot occur in UTF-8 text, so no combination of field values can
# imitate a field boundary. Joining on a printable character would mean
# ("a|b", "c") and ("a", "b|c") hashing identically -- two different ads, one
# token, and a mis-join that no test would think to look for.
_FIELD_SEP = b"\x1f"

# Same alphabet fly gates on, so the two reject the same strings.
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class DecodedRef(NamedTuple):
    form: str
    token: str


def mint_ref_token(
    study_id: str,
    stratum_id: str,
    creative_name: str,
    destination_name: str,
) -> str:
    """The opaque per-ad token, as lowercase hex.

    **Deterministic, and that is a hard requirement rather than a convenience.**
    Reconciliation compares creatives via `field_contract.COMPARED_AD`, and the
    ref is part of the creative. A random token would differ on every run, so
    every run would see every ad as changed and rewrite the study's entire ad
    set -- forever, and while spending money.

    The tuple is exactly the grain of an `ad_attributions` row: vlab creates one
    ad per (creative, stratum) pair, and `destination_name` is included because
    one study can run several destinations over the same strata and each is a
    separate ad with a separate row.

    `study_id` is in the digest even though lookups are per-study. It costs
    nothing and it means two studies sharing a stratum vocabulary -- which is
    common, since researchers copy confs -- do not mint identical tokens. That
    keeps the token meaningful if it is ever read outside a per-study context.
    """
    h = hashlib.blake2b(digest_size=REF_TOKEN_BYTES, person=_TOKEN_DOMAIN[:16])
    h.update(
        _FIELD_SEP.join(
            s.encode("utf-8")
            for s in (study_id, stratum_id, creative_name, destination_name)
        )
    )
    return h.hexdigest()


def encode_recruitment_ref(shortcode: str, token: str) -> str:
    """Pack a shortcode and a hex token into the opaque base64url payload.

    Raises ValueError on anything fly's decoder would reject, so a malformed ref
    is impossible to publish rather than merely detectable afterwards. The
    respondent-facing failure is expensive and asymmetric: fly throws
    RefDecodeError and the person lands in an ERROR state having clicked an ad
    we paid for.
    """
    sc = shortcode.encode("utf-8")

    if not 1 <= len(sc) <= 255:
        raise ValueError(
            f"shortcode '{shortcode}' is {len(sc)} bytes; the encoded ref "
            "carries the length in a single byte, so 1..255 is the limit"
        )

    raw = bytes.fromhex(token)

    if not raw:
        raise ValueError("ref token is empty; fly requires at least one byte")

    payload = bytes([ENCODED_REF_VERSION, len(sc)]) + sc + raw

    # Unpadded, because fly asserts canonicality by re-encoding the decoded
    # buffer and comparing -- Node's base64url output has no `=`, so padding
    # here would fail that check on every single ref.
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def encoded_ref(shortcode: str, token: str) -> str:
    """The full ref as it appears on the wire, anchor included.

    `r.` is the second anchor fly's WhatsApp entry gate accepts
    (WHATSAPP_ENTRY_REF_ENCODED in replybot/lib/event-normalizer.js) and the key
    `getMetadata` recognises on Messenger. It is a distinct anchor rather than a
    reuse of `form.` so that the two grammars can never be confused: `form.` is
    always dot-pairs, `r.` is always opaque, and neither has to be sniffed.
    """
    return f"r.{encode_recruitment_ref(shortcode, token)}"


def decode_recruitment_ref(encoded: str) -> DecodedRef:
    """Mirror of fly's decoder, for tests and config-time verification.

    vlab does not need this at runtime -- it is the producer. It exists so the
    contract can be exercised from this side alone, and so
    `check_encoded_refs_round_trip` can prove a study's own refs survive before
    a single ad is published.
    """
    if not _B64URL.match(encoded or ""):
        raise ValueError(f"encoded ref is not base64url: {encoded}")

    # Both checks are needed and they catch different things. Python rejects an
    # impossible *length* here (binascii.Error, a ValueError subclass, with a
    # message worth replacing); Node's decoder accepts it and silently returns a
    # SHORT buffer instead. The round-trip below is what catches that, plus the
    # case neither decoder rejects: a legal length carrying non-zero trailing
    # bits, which decodes fine and re-encodes to a *different* string.
    #
    # Together they mean one ref maps to one payload and back. Without them a
    # near-miss reads as a valid but different payload -- a silent mis-route
    # into another researcher's survey, which is the failure this format exists
    # to remove.
    try:
        buf = urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except BinasciiError as e:
        raise ValueError(
            f"encoded ref is not canonical base64url: {encoded}"
        ) from e

    if urlsafe_b64encode(buf).decode("ascii").rstrip("=") != encoded:
        raise ValueError(f"encoded ref is not canonical base64url: {encoded}")

    if len(buf) < 4:
        raise ValueError(f"encoded ref is too short: {encoded}")

    version = buf[0]
    if version != ENCODED_REF_VERSION:
        raise ValueError(f"unknown encoded ref version {version}: {encoded}")

    length = buf[1]
    if length < 1 or len(buf) < 2 + length + 1:
        raise ValueError(f"encoded ref shortcode length out of range: {encoded}")

    form = buf[2 : 2 + length].decode("utf-8")

    if not form.strip():
        raise ValueError(f"encoded ref carries an empty shortcode: {encoded}")

    return DecodedRef(form=form, token=buf[2 + length :].hex())
