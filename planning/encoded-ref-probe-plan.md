# Plan — the encoded-ref probe

**Date:** 2026-08-26
**Status:** not started. Preconditions verified below; nothing here has been run.
**Cost:** legs 0–2 are free. Leg 3 creates one `PAUSED` ad and spends nothing.
**Companion docs:** `planning/ctwa-probe-runbook.md` is the idiom this follows and
records a probe already run on 2026-08-17. `planning/encoded-ref-handover.md` §6c
frames the gap. `documentation/ad-attributions.md` is the mechanism.

---

## 0. Why this exists

Every layer of encoded-ref attribution is unit- and integration-tested, and the
golden vectors match across repos. The full path has still never carried a real
respondent:

```
adopt mints token -> ad on Meta -> respondent clicks -> fly decodes
  -> metadata.vt -> swoosh joins -> inference_data
```

That is the safety property and the gap at once. It is inert because nothing
opts in, and nothing opts in because nobody has proven it works.

**The failure mode is silence.** A ref fly cannot decode does not error — the
respondent lands in `FALLBACK_FORM` and looks like a completion. A token that
never comes back does not error either: it is now an *expected* arrival that
reports nothing. Which is the sharpest reason for this probe — see §5.

---

## 1. Already settled — do not re-test

Verified 2026-08-26 unless noted. Cited so the next person can re-check rather
than re-measure.

| Claim | Evidence |
|---|---|
| Deployed fly decodes `r.<payload>` | `replybot-v0.0.221` contains `WHATSAPP_ENTRY_REF_ENCODED`, `decodeRecruitmentRef`, and the `%XX`-widened `WHATSAPP_ENTRY_REF`. `kubectl -n vprod` and `-n vstag` both run `ghcr.io/vlab-research/replybot:v0.0.221`. |
| vlab is deployed | helm release `vlab` in `vprod` rev 137: adopt `v0.1.79`, swoosh `v0.1.11`. |
| The table exists | `ad_attributions` queryable in `vlab` on `gbv-cockroachdb-0`. Migrations `v0.2.0`; `20260816000000` and `20260818000000` applied. |
| The dashboard's endpoint is served | `/{org}/studies/{slug}/ad-attributions` returns 403 (auth) where a nonexistent route returns 404. |
| The feature is inert | 0 of 719 `destinations` confs carry `ref_mode`; 0 of 691 `inference_data` confs carry `mapping`. |
| Messenger is the only live transport | fly `planning/multi-platform-plan.md`, status 2026-08-26. |
| Routing and attribution are one decode | `encode_recruitment_ref` packs shortcode **and** token into one payload, so fly's decode yields both or neither. A decode failure is therefore *loud* (FALLBACK_FORM), not silent — for fly destinations only. |
| A failed fallback stays in the account | fly `7232c3b7`: `formcentral/db.go:82` resolves a survey by the owner of the account the conversation is already on. FALLBACK_FORM cannot cross researchers. |

---

## 2. The environment problem — read before planning a run

`planning/encoded-ref-handover.md` §6a step 4 says "opt one staging study in."
**That path is not available.** Two independent blockers, both verified:

- `devops/values/toixo-staging.yaml` pins `versionAdopt: v0.0.106` against
  production's `v0.1.79`. It has none of this code.
- It has **no `migrations:` block**, and the chart's `values.yaml` has no
  default, so the pre-upgrade hook would template an empty image reference.
  Staging cannot run migrations at all.

So the choice is: rehabilitate vlab staging first (a larger and riskier change
than the probe), or run the probe against production with a study built for it.
**Recommend the latter**, because legs 0–2 touch nothing live and leg 3 creates a
`PAUSED` ad that never spends — the same posture `ctwa-probe-runbook.md` used
successfully on 2026-08-17.

---

## 3. The legs

Ordered by cost. Each is independently useful; stop wherever the answer stops
being worth the next leg's price.

### Leg 0 — does the write half produce a row at all? (free)

**`ad_attributions` currently holds zero rows.** Not zero *with tokens* — zero
rows, full stop:

```sql
SELECT count(*), count(ref_token) FROM ad_attributions;   -- 0 | 0
```

Rows are written only on ad **creates**, and a steady-state study reconciles by
update, so zero is *consistent* with a healthy write path that has had nothing
to do. It is equally consistent with `record_ad_attribution` never firing. Those
two are indistinguishable from the outside, and every later leg assumes the
first.

**Do:** find the most recent `"ad"`/`"create"` instruction any study issued since
adopt v0.1.78 shipped, and check whether a row followed. If no study has created
an ad in that window, this leg is answered by leg 3 instead — say so rather than
inferring health from an empty table.

**Answers:** whether the write half works. Everything downstream is moot if not.

### Leg 1 — the deploy contract (free, permanent)

The check that would have caught the thing this project already got wrong once:
code existing on a *branch* while a *tag* is what runs.

adopt's `decode_recruitment_ref` is a **reimplementation** of fly's decoder, and
the WhatsApp regex in adopt's tests is a **verbatim copy** of fly's. Both are
vendored, and nothing detects drift.

**Do:** a shared fixture of v1 vectors — `(shortcode, token) -> encoded ref`.
vlab asserts it *mints* them; fly asserts its **deployed tag** *decodes* them.
Neither repo needs the other checked out. Fly's half reads `versionReplybot` out
of `devops/values/production.yaml` so the assertion is against what runs, not
against `main`.

**Recommend the vectors live in vlab beside `ref_encoding.py`**, since that is
what mints them, and fly consumes them. Invert only if fly should own the format.

**Answers:** does the tag we run decode what the tag we run mints — now, and on
every future change to either side.

### Leg 2 — does Meta deliver base64url intact? (free)

Base64url is `A-Za-z0-9-_`, all inside fly's gate alphabet, so it *should*
survive. "Should" is what this project keeps being wrong about.

**Do:** extend `adopt/scripts/ctwa_probe.py` to build an encoded-mode creative
and read back all three carriers off the live ad:

| Carrier | Field | Reaches |
|---|---|---|
| `url_tags` | `ref=r.<payload>` | Messenger `referral.ref` (~32% of entrants) |
| quick-reply payload | inside `page_welcome_message` | Messenger (~68%, their only carrier) |
| `autofill_message.content` | inside `page_welcome_message` | WhatsApp (its only carrier) |

Compare each byte-for-byte against `dotted_ref` / `whatsapp_ref` output. One-shot
measurement; the result belongs in `documentation/ad-attributions.md`, not in a
test that reruns forever.

**Answers:** whether Meta mangles the payload. If it does, the format changes and
legs 3+ are void.

### Leg 3 — one real arrival, end to end (one PAUSED ad, no spend)

The only leg that proves the thing.

**Do:** build a study with one Messenger destination in `ref_mode: "encoded"` and
one `ad_table_lookup` conf (`location: metadata`, `key: vt`, `name:` a stratum
variable the ad is frozen with). Create the ad `PAUSED`. Click the preview —
measured 2026-08-16 to produce genuine referrals with no activation, review or
spend. Then walk the chain:

1. `ad_attributions` has a row for the ad, with a non-NULL `ref_token`
2. replybot logs a decode: `md.form` is the shortcode, `md.vt` the token
3. the respondent lands in the intended survey, **not** `FALLBACK_FORM` (305)
4. `swoosh` emits **no** `ad=unmapped` event for the study
5. `inference_data` carries the declared variable for that user

**Messenger first, deliberately.** It is the only live transport, and its two
carriers cover both Meta referral paths. WhatsApp repeats the same walk once it
is a live transport; the autofill leg is measured in leg 2 regardless.

**Answers:** everything.

### Leg 4 — the web/app bare token (descoped; say so out loud)

A web or app destination in `ref_mode: "encoded"` interpolates a **bare** token
into `url_template`. Unlike the fly destinations, routing does not depend on it —
the template already points at the survey — so routing and attribution are
**decoupled**, and a token that fails to reach the survey platform produces a
perfectly successful respondent who is silently unattributed.

This leg needs a real Typeform or Qualtrics with a hidden field, which we do not
have. **Do not fake it.** Until someone runs it, the honest position is that this
path has no production evidence, and it belongs in
`documentation/ad-attributions.md` as a stated limit rather than an implied
capability.

---

## 4. Open question, unverified

Does the `(platform, account_id, user_id)` threading change the shape of
`User.ID` reaching swoosh through the fly connector? If a respondent's id shape
shifts mid-study, swoosh sees two people where there is one — the same
silent-miscount family as everything above, arriving from a different direction.
Rows are currently being stamped with `account_id` (8,800 of 106,994,949 as of
2026-08-26), so any change would be arriving gradually right now.

Check before leg 3, since leg 3's step 5 depends on the answer.

---

## 5. The observability gap this probe compensates for

Retiring the organic counter was correct — with a lookup now valid on
`location: "variable"`, "no token" is genuinely ambiguous, and a study may
legitimately recruit organically. But the consequence is real: **a
correctly-configured encoded study whose refs stop round-tripping now emits no
signal at all.** Its strata simply count zero.

Under the previous three-way split it would have flooded organic warnings.
`thins_its_ref_without_reading_the_mapping` does not help — it fires only when a
study declares *no* lookup conf, which a correctly-configured study does not.

Two ways to close it, and this is a decision, not a task:

1. **Accept it, and let the probe stand in.** Defensible while the feature is
   opt-in and one study wide.
2. **A rate signal conditioned on opt-in** — a study whose confs declare a
   lookup, seeing a sustained zero-token rate, is broken. Different from the old
   counter: conditioned on having opted in, and a rate rather than a per-event
   classification, so it cannot be inflated by legitimate organic arrivals.

Option 2 is the durable answer if this feature is ever to run unattended.

---

## 6. Order

```
leg 0  ─ free        ─ does the write half work
leg 1  ─ free        ─ does the deployed tag decode the deployed mint   (permanent guard)
leg 2  ─ free        ─ does Meta deliver the payload intact
leg 3  ─ one PAUSED ad ─ does a real arrival attribute
leg 4  ─ blocked     ─ needs a survey platform we do not have
```

Legs 0–2 are prerequisites for trusting leg 3's result, not merely cheaper.
