"""Conformance tests for slugify.py against real `gosimple/slug` output.

Every expectation in this file was produced by running
`github.com/gosimple/slug v1.12.0`.`Make` — the exact version pinned in
`api/go.mod` — over the inputs below, not by reasoning about what it ought to
do. That distinction earned its keep: the first draft of `slugify.py` missed
`languages_substitution.go`'s `init()`, which merges `defaultSub` (quote
deletions and the four dash variants) into every language map. Reading the
library's `enSub` literal alone gives you "nandan-s-study" where the dashboard
gives you "nandans-study", and nothing but a differential test catches it.

To regenerate after a `gosimple/slug` bump, run against the new version:

    for _, s := range inputs { fmt.Printf("%q -> %q\\n", s, slug.Make(s)) }

with `inputs` being the table below plus `_sweep_inputs()`.
"""

import hashlib

from .slugify import slugify

# (name, slug.Make(name)) — recorded from Go.
GOLDEN = [
    ("Simple Name", "simple-name"),
    ("simple", "simple"),
    ("SIMPLE NAME", "simple-name"),
    ("MiXeD CaSe StUdY", "mixed-case-study"),
    ("  leading and trailing  ", "leading-and-trailing"),
    ("a  b   c", "a-b-c"),
    ("a - b - c", "a-b-c"),
    ("a---b", "a-b"),
    # Underscores are authorized characters, so they survive verbatim and are
    # NOT collapsed the way dashes are.
    ("a___b", "a___b"),
    ("_underscore_", "underscore"),
    ("-dash-", "dash"),
    ("--__--", ""),
    ("Nigeria Smoke Study 2024", "nigeria-smoke-study-2024"),
    ("study/with/slashes", "study-with-slashes"),
    ("study.with.dots", "study-with-dots"),
    ("study,with,commas", "study-with-commas"),
    ("100% coverage!", "100-coverage"),
    # "&" and "@" are substituted, not dashed, and before transliteration.
    ("R&D study", "randd-study"),
    ("R & D", "r-and-d"),
    ("me@example.com", "meatexample-com"),
    ("a&b@c", "aandbatc"),
    # Accented Latin.
    ("Ünïcödé Stüdy", "unicode-study"),
    ("Café Zürich", "cafe-zurich"),
    ("Åland Ø Æ", "aland-o-ae"),
    ("Señor Muñoz", "senor-munoz"),
    ("François Déjà Vu", "francois-deja-vu"),
    # Expansions: one character becomes several ASCII ones.
    ("Groß Straße", "gross-strasse"),
    ("ß", "ss"),
    ("Ærøskøbing", "aeroskobing"),
    ("İstanbul", "istanbul"),
    ("Ĳsselmeer", "ijsselmeer"),
    ("Ñandú", "nandu"),
    # Non-Latin scripts are romanised, not dropped. This is the reason
    # slugify.py carries the whole transliteration table: a Latin-only
    # implementation would slug all of these to "" and produce an
    # unaddressable study.
    ("Москва исследование", "moskva-issledovanie"),
    ("Привет мир", "privet-mir"),
    ("Ελληνικά μελέτη", "ellenika-melete"),
    ("北京 研究", "bei-jing-yan-jiu"),
    ("日本語のスタディ", "ri-ben-yu-nosutadei"),
    ("한국어 연구", "hangugeo-yeongu"),
    ("دراسة عربية", "drs-rby"),
    ("מחקר עברי", "mkhqr-bry"),
    ("अध्ययन हिंदी", "adhyyn-hindii"),
    ("การศึกษาไทย", "kaarsueksaaaithy"),
    # Above the BMP (emoji, flags) is dropped entirely — not even a dash.
    ("study 😀 emoji", "study-emoji"),
    ("😀😀😀", ""),
    ("🇳🇬 Nigeria", "nigeria"),
    # Symbols and currency.
    ("études françaises № 5", "etudes-francaises-5"),
    ("50€ budget", "50eu-budget"),
    ("£10 study", "ps10-study"),
    ("©2024 study", "c-2024-study"),
    ("½ study", "1-2-study"),
    ("Ⅷ roman", "viii-roman"),
    ("ﬁne ligature", "fine-ligature"),
    ("a\tb\nc", "a-b-c"),
    # Everything here slugs to the empty string.
    ("  ", ""),
    ("!!!", ""),
    ("...", ""),
    ("-", ""),
    ("_", ""),
    ("", ""),
    ("123", "123"),
    ("2024-01-01 baseline", "2024-01-01-baseline"),
    ("study(1)", "study-1"),
    ("study [draft]", "study-draft"),
    ("study {v2}", "study-v2"),
    ("study <alpha>", "study-alpha"),
    # Quotes are DELETED (defaultSub), dashes of all four kinds become "-".
    ("naïve café — em dash", "naive-cafe-em-dash"),
    ('quote\'s "study"', "quotes-study"),
    ("back`tick", "back-tick"),
    ("tilde~study", "tilde-study"),
    ("plus+study", "plus-study"),
    ("equals=study", "equals-study"),
    ("hash#study", "hash-study"),
    ("dollar$study", "dollar-study"),
    ("caret^study", "caret-study"),
    ("star*study", "star-study"),
    # ":" is 0x3A, which would fall inside a "9-_" range. Go's
    # `[^a-zA-Z0-9-_]` does not create that range — the "-" is a literal — and
    # these cases pin that reading down.
    ("semi;colon", "semi-colon"),
    ("colon:study", "colon-study"),
    ("question?study", "question-study"),
    ("pipe|study", "pipe-study"),
    ("back\\slash", "back-slash"),
]


def test_golden_cases_match_gosimple():
    mismatches = [
        (name, expected, slugify(name))
        for name, expected in GOLDEN
        if slugify(name) != expected
    ]
    assert mismatches == []


def test_long_names_are_not_truncated():
    # slug.MaxLength defaults to 0 (off) and api/ never sets it, so there is
    # no smartTruncate step to port.
    assert slugify("a" * 300) == "a" * 300
    assert slugify("ñ" * 150) == "n" * 150


def _sweep_inputs():
    """Every BMP codepoint in leading, trailing, interior and repeated position.

    Position matters because the pipeline's final step trims "-" and "_" only
    at the ends, and because `strings.TrimSpace` (which we approximate with
    `str.strip()`, see slugify.py) only ever touches the ends.
    """
    for c in range(0x0, 0x10000):
        if 0xD800 <= c <= 0xDFFF:
            # Lone surrogates are not valid Python strings' business and
            # cannot survive JSON decoding, so no request can carry one.
            continue
        ch = chr(c)
        yield "a" + ch + "b"
        yield ch + "ab"
        yield "ab" + ch
        yield ch + "a" + ch + "b" + ch


# sha256 over `src \0 slug \1` for each of the sweep inputs, in order, computed
# from real `gosimple/slug` v1.12.0 output. A digest rather than 254k literals:
# it fails loudly on any divergence, and the failure message tells you to
# re-run the Go generator to find out where.
SWEEP_COUNT = 253952
SWEEP_SHA256 = "ea561ffc6a5315bbd5f00800283c3872345ee69f0ad00c269dcdee26f76c6b72"


def test_exhaustive_bmp_sweep_matches_gosimple():
    h = hashlib.sha256()
    n = 0
    for src in _sweep_inputs():
        h.update(src.encode("utf8"))
        h.update(b"\x00")
        h.update(slugify(src).encode("utf8"))
        h.update(b"\x01")
        n += 1

    assert n == SWEEP_COUNT
    assert h.hexdigest() == SWEEP_SHA256, (
        "slugify() no longer agrees with gosimple/slug v1.12.0 over the BMP. "
        "Re-run the Go generator in the module docstring to find the diverging "
        "codepoints before changing this digest."
    )
