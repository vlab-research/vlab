# The creative construction contract

**Date:** 2026-08-30
**Status:** Design agreed, not implemented.
**Why it exists:** a day was lost to three separate Meta rejections that were
all the same bug, fixed one at a time in the order Meta happened to surface
them. This is the enumeration that would have prevented that.

---

## 0. The invariant nobody had written down

A Meta messaging ad states its destination in **three** places:

| # | Where | Shape |
|---|---|---|
| 1 | ad set `destination_type` | a single enum token |
| 2 | creative `object_story_spec.link_data.call_to_action` | single-valued, the fallback |
| 3 | creative `asset_feed_spec.call_to_actions` + `optimization_type` | the array; multi-destination only |

**Meta requires all three to agree.** Error subcode `2490279` — *"Inconsistent
Campaign Destination Type With App Destination"* — is the sound of them
disagreeing. It names neither the ad set nor the conf, which is why it costs
hours.

The bug generator is that adopt sourced them **differently**: #1 and #2 from the
study conf, #3 from the template ad. Every specific failure was an instance of
that.

## 1. The decision: vlab constructs, the template contributes content

Four positions were considered. Naming them, because the rejected ones will look
attractive again later:

1. **Full construct.** adopt builds the ad from the conf; the template
   contributes creative content only. **← chosen**
2. **Destination from conf, everything else copied.** The status quo. Mixed
   ownership, and the source of this document.
3. **Minimal remix.** Copy the template verbatim except ref-bearing fields;
   derive even the ad set's `destination_type` from the template's CTAs, so
   Facebook owns every contract and vlab only injects routing.
4. **No remix.** Impossible — the ref has to go somewhere.

**Why not 3**, which was argued at length and is genuinely attractive: it does
not escape the Facebook knowledge, it converts a *constructor* into a
*recogniser*, and recognisers are strictly harder. Construction is closed-world
— emit one known-good shape per destination type, snapshot-test it, and fail
with "we don't support that yet". Recognition is open-world — you must correctly
handle arbitrary Ads Manager output including shapes Meta has not shipped yet,
and every bug in this document was already of the form "we didn't anticipate
that input".

Three further arguments for 1 that decided it:

- **Determinism.** Same conf → byte-identical creative. Under 3 the ad depends
  on what a human built in Ads Manager last Tuesday. The creative is an
  experimental condition; it cannot drift silently.
- **Combinatorics.** vlab's model is strata × creatives × destinations.
  Construction scales that for free; templates make a human hand-build the cross
  product, multiplicatively, in exactly the dimension vlab exists to exploit.
- **Testability.** `conf → creative` can be tested exhaustively. A recogniser
  can only be tested against inputs someone thought of.

The cost of 1 is real and accepted: vlab owns every Facebook contract, and new
Meta features need adopt work before a researcher can use them. Both were
**already true** — adopt was at position 2 and already constructed most of the
ad.

## 2. The finding that makes this small

**`_create_creative` is already an allowlist, everywhere except one field.**

- `fields_to_copy` — an explicit five-name list (`actor_id`,
  `degrees_of_freedom_spec`, `instagram_user_id`, `thumbnail_url`,
  `contextual_multi_ads`).
- `link_data` — reconstructed key by key. **`call_to_action` is constructed**,
  passed in as a parameter, never copied from the template.
- `photo_data` — converted to `link_data` rather than copied.
- `video_data` — its own explicit copy list.
- `object_story_spec` — rebuilt from scratch, only `page_id` and
  `instagram_user_id` carried over.

The single exception:

```python
tafs = asset_feed_spec if asset_feed_spec is not None else template_afs
```

`asset_feed_spec` is copied as an **opaque blob**. It is also the only field
besides the CTA that carries destination. Every failure below came through that
one hole.

So the work is not a rewrite. It is giving `asset_feed_spec` the treatment
`object_story_spec` already gets.

## 3. What went wrong, in order, and why each was the same bug

All three on `vl-pulse-nigeria-smoke`, 2026-08-30.

**(a) The template's Instagram CTA.** The selected template ad was a
Messenger+Instagram click-to-messaging ad. Its `asset_feed_spec` carried
`INSTAGRAM_MESSAGE → INSTAGRAM_DIRECT`, copied through untouched, into an ad set
adopt had built as `MESSENGER`. Meta: `2490279`.

**(b) The destination union was not discriminated.** Separately,
`DestinationConf` was a plain `Union` resolved by *shape*.
`FlyMessengerDestination` came first and declared `type: str`, so it matched any
tag — and a multi conf carries every field a Messenger conf requires, with
`whatsapp_phone_number` merely ignored as an extra. **`FlyMultiDestination` was
unreachable**; `type: "multi"` never once produced one. So the study derived a
MESSENGER ad set and injected no multi `asset_feed_spec`, and the template's own
WhatsApp CTA passed through. Meta: `2490279` again, for a different reason.

Fixed in `d382000c`. Note the rejection was *luck*: with a Messenger-only
template, the same conf builds a Messenger-only ad for a study configured as
multi, and nothing anywhere reports it.

**(c) The `asset_feed_spec` collision.** With (b) fixed the destination really
was multi, so adopt tried to inject its own spec and hit the guard refusing to
run over a template that already had one. But the template's spec was
**byte-equivalent** to what adopt would construct — same `optimization_type`,
same two Meta sample URLs. The guard's stated reason ("using the template's
would drop the destination array and the ad would only ever open Messenger") was
false for that template. The guard was written for a template carrying a
*different* `optimization_type` and could not tell the two apart.

Each fix revealed the next because none addressed the sourcing split.

## 4. The contract

For every field a template can carry, exactly one of three dispositions.

### COPY — creative content

The researcher chose it and it does not encode destination.

| Field | Note |
|---|---|
| `actor_id` | already in `fields_to_copy` |
| `instagram_user_id` | already; see open question §6.1 |
| `thumbnail_url` | already |
| `degrees_of_freedom_spec` | Advantage+ opt-ins — **content**, they change what respondents see |
| `contextual_multi_ads` | placement opt-in |
| `link_data.image_hash` / `message` / `name` / `description` | already reconstructed |
| `video_data.*`, `photo_data.*` | already handled |
| `asset_feed_spec`: `bodies`, `titles`, `descriptions`, `images`, `videos`, `ad_formats`, `link_urls` | **new** — the Advantage+ variant fields, currently riding along inside the opaque blob |

### CONSTRUCT — vlab owns it

Destination and routing. Derived from the study conf, never read from the
template.

| Field | Source |
|---|---|
| ad set `destination_type` | `destination_type_for(destination)` |
| `link_data.call_to_action` | already constructed |
| `asset_feed_spec.call_to_actions` | `multi_destination_asset_feed_spec()` |
| `asset_feed_spec.optimization_type` | `DOF_MESSAGING_DESTINATION` for multi |
| `asset_feed_spec.additional_data.page_welcome_message` | the ref |
| `url_tags` | the ref |
| `name` | the creative name — a join key for `mint_ref_token` |

### REFUSE — intent-bearing disagreement

Not silently dropped. A researcher who built an Instagram destination *meant*
it, and quietly shipping a Messenger ad is the same silent-misroute failure this
codebase fights everywhere else.

The rule is **disagreement, not presence** — refusing any template carrying a
CTA would refuse every template Ads Manager can produce.

Read the destination set the template declares — the `app_destination` values
under `asset_feed_spec.call_to_actions` — and compare it to what the conf's
destination implies. Refuse on mismatch, naming both sets.

This is a *closed-world* check (does this small set of strings equal that one?),
not the open-world recognition that sank position 3. We are not reconciling two
sources of truth; there is one, plus a cheap assertion that the researcher's
template did not mean something else.

`messaging_destinations_of()` was drafted for this and its role changes: it no
longer reconciles, it only reads what the template claims so a mismatch can be
refused before construction.

### The three `asset_feed_spec` cases

`optimization_type` is single-valued, which is the original guard's real
insight, and it survives — correctly scoped:

| Template's `optimization_type` | Study needs | Disposition |
|---|---|---|
| absent | multi | construct ours |
| `DOF_MESSAGING_DESTINATION` | multi | check destinations agree, then construct ours; copy the variant fields |
| anything else (Advantage+) | multi | **genuine conflict** — refuse. One spec, one `optimization_type`; the destination array and the creative variants cannot both apply |
| anything | single-destination | copy the template's; no destination array needed |

## 5. Where the check lives

**adopt only, at optimize time.** Explicitly *not* in the dashboard.

Destinations and creatives are separate confs POSTed to separate endpoints and
saved in any order, so at template-selection time there may be no destination to
check against. adopt is authoritative and a cron-time failure naming the fields
is acceptable.

## 6. Open questions

### 6.1 Does the page move to the conf?

`page_id` / `actor_id` currently come from the template. "Which page, which
WhatsApp number" is *intent*, not creative content, so under §1 it belongs in
the conf. Long run the template could shrink to an image hash plus copy — a far
smaller Facebook surface to read, even as adopt writes more.

Separable from the contract; should not block it.

### 6.2 A way to see the creative without deploying

The single biggest process failure: every hypothesis cost a release plus a cron
cycle, so the three bugs were learned serially instead of together.

Wanted: print the creative adopt *would* build for a given study and stratum,
no deploy, no cron. `adopt-probe` already does something adjacent for live ads.
This is what makes §4's enumeration reviewable in one run, and how we verify the
allowlist has not dropped something researchers depend on.

Build this **before** implementing §4.

## 7. Deliberately not doing

- **Template-authoritative destination** (position 3) — §1.
- **Dashboard-side checking** — §5.
- **Silently dropping intent-bearing fields** — §4.
- **Reconciling the template's `asset_feed_spec` with a constructed one.** There
  is one source of truth. The abandoned patch that tried to merge them was a
  third special case on the same broken seam.
