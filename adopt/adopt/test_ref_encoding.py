import pytest

from .ref_encoding import (
    ENCODED_REF_VERSION,
    REF_TOKEN_BYTES,
    decode_recruitment_ref,
    encode_recruitment_ref,
    encoded_ref,
    mint_ref_token,
)

# GOLDEN VECTORS -- the cross-repo contract, byte for byte.
#
# Produced by this encoder and verified against fly's shipped decoder
# (replybot/lib/typewheels/utils.js decodeRecruitmentRef) on 2026-08-18. If a
# change to this module makes these fail, the change breaks every live encoded
# ad, because fly is already deployed against exactly these bytes. Regenerating
# them to make the test pass is the wrong fix -- bump ENCODED_REF_VERSION.
GOLDEN = [
    ("mnchweek", "5e1cd2e7c2", "AQhtbmNod2Vla14c0ufC"),
    ("a", "5e1cd2e7c2", "AQFhXhzS58I"),
    ("café", "5e1cd2e7c2", "AQVjYWbDqV4c0ufC"),
    ("MNCH-week_2", "5e1cd2e7c2", "AQtNTkNILXdlZWtfMl4c0ufC"),
    ("ecdenglishincentive", "5e1cd2e7c2", "ARNlY2RlbmdsaXNoaW5jZW50aXZlXhzS58I"),
]


@pytest.mark.parametrize("shortcode,token,expected", GOLDEN)
def test_encoding_matches_the_bytes_fly_already_decodes(shortcode, token, expected):
    assert encode_recruitment_ref(shortcode, token) == expected


@pytest.mark.parametrize("shortcode,token,expected", GOLDEN)
def test_round_trip(shortcode, token, expected):
    assert decode_recruitment_ref(expected) == (shortcode, token)


def test_the_ref_carries_its_anchor():
    """`r.` is what both of fly's entry points key on."""
    assert encoded_ref("mnchweek", "5e1cd2e7c2") == "r.AQhtbmNod2Vla14c0ufC"


@pytest.mark.parametrize("shortcode,_token,encoded", GOLDEN)
def test_stays_inside_the_alphabet_both_entry_gates_accept(shortcode, _token, encoded):
    """No `.`, so it can never be mistaken for the dotted key/value grammar.

    This is what lets fly tell the two ref formats apart by anchor alone rather
    than by sniffing content, and what lets an encoded ref through the WhatsApp
    entry gate without percent-escapes.
    """
    assert all(c.isalnum() or c in "_-" for c in encoded)
    assert "." not in encoded


def test_a_multi_byte_shortcode_survives():
    """The length prefix is in BYTES; slicing by characters would truncate."""
    assert decode_recruitment_ref(encode_recruitment_ref("café", "0102030405")).form == "café"


# --- token minting ---------------------------------------------------------


def test_minting_is_deterministic():
    """Non-negotiable: the ref is part of the creative.

    A token that varied between runs would make reconciliation see every ad as
    changed and rewrite the study's whole ad set on every single run, forever,
    while spending money.
    """
    a = mint_ref_token("study", "stratum", "creative", "dest")
    b = mint_ref_token("study", "stratum", "creative", "dest")

    assert a == b


def test_every_component_of_the_grain_changes_the_token():
    base = ("study", "stratum", "creative", "dest")
    tokens = {mint_ref_token(*base)}

    for i in range(len(base)):
        changed = list(base)
        changed[i] = changed[i] + "-x"
        tokens.add(mint_ref_token(*changed))

    assert len(tokens) == len(base) + 1


def test_field_boundaries_cannot_be_forged():
    """("a","b",..) and ("ab","",..) must not collide.

    They would under any printable separator, which is why the digest uses a
    byte that cannot occur in UTF-8 text. A collision here means two different
    ads sharing one attribution identity.
    """
    assert mint_ref_token("a", "b", "c", "d") != mint_ref_token("ab", "", "c", "d")
    assert mint_ref_token("a", "b", "c", "d") != mint_ref_token("a", "bc", "", "d")


def test_token_is_the_declared_width():
    token = mint_ref_token("s", "st", "c", "d")

    assert len(token) == REF_TOKEN_BYTES * 2
    assert token == token.lower()
    bytes.fromhex(token)


# --- refusing to publish something fly would reject ------------------------


def test_an_over_long_shortcode_is_refused():
    """The length lives in one byte, so 256 is unrepresentable."""
    with pytest.raises(ValueError, match="255"):
        encode_recruitment_ref("x" * 256, "0102030405")


def test_an_empty_shortcode_is_refused():
    with pytest.raises(ValueError):
        encode_recruitment_ref("", "0102030405")


def test_an_empty_token_is_refused():
    with pytest.raises(ValueError, match="at least one byte"):
        encode_recruitment_ref("mnchweek", "")


@pytest.mark.parametrize("bad", ["not base64!", "has.dot", "plus+slash/", ""])
def test_decoding_rejects_anything_outside_the_alphabet(bad):
    with pytest.raises(ValueError, match="base64url"):
        decode_recruitment_ref(bad)


def test_decoding_rejects_a_lenient_near_miss_rather_than_truncating():
    """Both decoders skip unusable trailing bits instead of failing.

    So a string of impossible length decodes to a SHORT buffer and would read as
    a valid but *different* payload -- a silent mis-route. The canonicality
    check is the only thing standing between that and a wrong survey.
    """
    with pytest.raises(ValueError, match="canonical"):
        decode_recruitment_ref(encode_recruitment_ref("mnchweek", "5e1cd2e7c2") + "A")


def test_decoding_rejects_an_unknown_version():
    payload = encode_recruitment_ref("mnchweek", "5e1cd2e7c2")
    import base64

    raw = bytearray(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    raw[0] = ENCODED_REF_VERSION + 1
    bumped = base64.urlsafe_b64encode(bytes(raw)).decode().rstrip("=")

    with pytest.raises(ValueError, match="version"):
        decode_recruitment_ref(bumped)
