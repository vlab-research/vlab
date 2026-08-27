# Ref mode in the dashboard — how a researcher chooses attribution

**Status:** **BUILT.** Shipped as `e7683333` (2026-08-24), "feat(dashboard): the
ref-mode control, and one extraction form", on `main`. This document captures the
decision reached 2026-08-21 and is kept as the record of *why* the control looks
the way it does; §1's "not exposed in the dashboard at all" describes the state
before that commit, not now.

Every decision below landed as written: two choices and no thin mode
(`refModeOptions()` returns exactly `metadata` and `encoded`), the model keeping
`ref_mode` `Optional` so an untouched conf resolves to legacy, the encoded
default living in the empty-state constructors rather than the schema, and
`displayedRefMode` reporting without writing back so an unrelated edit cannot
coerce a legacy conf. `Destination.test.tsx` pins that last one directly.

What this unblocked: `vlpulseng` stalled on 2026-08-21 partly because ref mode
was API-only and needed an Auth0 bearer token. It does not any more — the whole
study is configurable in the dashboard. See
`planning/encoded-ref-probe-runbook.md`.
**Scope:** the dashboard UX for how a study's ads carry attribution, and the
model/UI split that makes it migration-safe.
**Reads with:** `documentation/ad-attributions.md` (the join, both sides),
`documentation/multi-destination-ads.md`, `adopt/adopt/study_conf.py`
(`RefModeDestination`, `resolved_ref_mode`), `inference/swoosh/inference_data.go`
(`extractValue`, `adAttributionOutcome`).

---

## 1. The problem

A recruitment ad carries a **ref** — the string Meta returns to fly on a click.
The ref is the entire link between "someone clicked this ad" and "this response
belongs to women, 25–34, in Kwara." How much the ref carries, and how attribution
is recovered from it, is today an *implementation* detail (`ref_mode`) that:

- is **not exposed in the dashboard at all** — no `ref_mode` field, no
  `include_metadata_in_ref` field (deliberately omitted, per the comment in
  `dashboard/src/types/conf.ts`); and
- when it *is* set (only reachable via the API), splits across **two unrelated
  forms** — the write side (`ref_mode` on a destination) in Destinations, the
  read side (`mapping: "ad_table_lookup"` on a variable) in Variables.

Set one half without the other and attribution fails **silently**: encoded ads
whose tokens map to nothing, every arrival "unmapped", discovered hours later in
a swoosh log. The researcher was never asked a question they could answer, and
was given two ways to get it half-right.

## 2. What the researcher actually decides

A researcher never wants `ref_mode: "encoded"`. They want, at most, two things:

1. **Attribute respondents to the stratum that recruited them.** If they
   stratified at all — the whole product — this is always true. It is the task,
   not a preference.
2. **Don't show the respondent an ugly, editable tracking string.** Only matters
   on WhatsApp/multi, where the ref sits in the compose box. Invisible on
   Messenger, so the question does not arise there.

Everything else — thick, thin, encoded, `vt`, `ad_table_lookup` — is mechanism.
The UI must model the task, not the mechanism, and not mirror the engine's
write/read decomposition.

## 3. The modes, and why only two survive

| mode | ref on the wire | attribution | respondent sees |
|---|---|---|---|
| **thick** (`metadata`) | `creative.X.gender.women.form.Y` — everything inline | inline, no DB | long, readable/editable on WhatsApp |
| **thin** (`shortcode`) | `form.Y` — form only | **nobody** | clean |
| **encoded** | `r.<base64url(v1\|len\|shortcode\|token)>` | via `ad_attributions` join on `ref_token` | clean, opaque |

**Thin is dead.** It was only ever the WhatsApp/multi default, and there is **no
production population on those channels** — a destination-type census on
2026-08-21 returned 892 messenger, 11 web, 3 website, **0 whatsapp, 0 multi**. So
"clean ref that attributes nobody" has no stored conf to preserve. Delete it from
the surface entirely: making the footgun *unreachable* beats discouraging it.

That leaves two:

- **Thick** — inline, self-contained. Correct and free on Messenger (invisible
  ref, no DB). The "legacy but useful" path.
- **Encoded** — clean *and* attributes. The right answer for any visible-ref
  channel, and uniform across all channels.

## 4. Decisions

### 4.1 Two choices, encoded default, uniform across channels

The UI offers **encoded (default)** and **thick**. Not a three-way `ref_mode`
dropdown — the word "encoded" need not appear as jargon; frame by consequence
(§4.4).

Uniformity is the point, and it is a *data* argument, not a purity one: if
Messenger were thick and WhatsApp encoded, a multi-channel study would attribute
two different ways, and the researcher joins their data two different ways
depending on which arm a respondent came through — a confusion that surfaces at
analysis time, months later, to someone who was not in the room. Encoded
everywhere means one answer to "how do I get the stratum for this respondent":
join on `ref_token`. Same for every channel.

**Thick is offered on pure-Messenger studies only.** Its one cost — a visible,
editable ref — lands entirely on the WhatsApp arm, so offering it on WhatsApp or
multi would reintroduce the per-channel heterogeneity we are removing. Messenger
studies may pick thick (it is free there); WhatsApp and multi are encoded-only.

### 4.2 The model defaults to legacy; the UI drives the encoded default

This is the load-bearing split.

- **Model layer:** `ref_mode: Optional[RefMode] = None`, and `None` keeps
  resolving to legacy per channel (`resolved_ref_mode`). **Do not change the
  model default.** It is what keeps the migration free — an untouched conf
  resolves to exactly what it does today, with nobody rewriting stored JSON.
  Change it and you re-interpret every study in the database at once.
- **UI layer:** the dashboard writes `ref_mode` **explicitly** into every new
  destination payload — `"encoded"` for the default, `"metadata"` if a Messenger
  study picks thick. The encoded default lives in the form's *initial value*, not
  the schema.

Consequence, adopted as a convention:

> **`ref_mode is None` ⟺ created before this feature existed** (a legacy
> Messenger study, which is thick).

New studies never produce `None`. That makes "is this a legacy study?" a
one-field check and distinguishes "chose thick deliberately" from "predates the
choice." Since there are no legacy WhatsApp studies, `None` in practice means
exactly one thing: **thick Messenger.**

### 4.3 The sharp edge: "UI default" is *new-conf*, never *coerce-on-save*

If "encoded default" is the form's value rather than the form's *initial value
for a new conf*, then opening a legacy thick Messenger study, editing the welcome
message, and saving re-serializes `ref_mode` from `None → "encoded"` — a silent
flip of a running study (see §5). The rule:

- **New destination:** form initializes to encoded, writes `ref_mode: "encoded"`.
- **Editing an existing destination:** form **hydrates from the stored
  `ref_mode`** — including `None` — and preserves it. It never imposes the UI
  default on load.
- **Changing the mode on a study that already has arrivals:** guarded (§5).

The two defaults (model=legacy, UI=encoded) only coexist if the UI default is
strictly a new-conf affordance and edit-load is faithful to stored state.

### 4.4 Frame each mode by its data consequence, not its name

Attribution cannot be fully hidden, because the mode changes the **shape of what
the researcher gets out** for any analysis outside the standard
swoosh→`inference_data` pipeline:

- **Thick:** stratum values ride inline in every response's metadata. Their
  export already has `gender`, `region` columns. Self-contained.
- **Encoded:** the response carries a token; the stratum lives in a **separate**
  `ad_attributions` table they join on `ref_token`.

So the one thing to inform is not "encoded vs thick" but: *"with encoded, your
stratum data is in the ad-attributions export, joined on `ref_token`."* Give them
the table and name the key. That is the researcher-facing contract.

**`ref_token` is a verification surface, not an input.** After ads build, show
the researcher the `ad_attributions` rows (a table, or the
`…/studies/<slug>/ad-attributions.csv` export — which today has **no download
button**; add one). Each ad, its stratum, its `ref_token`. "Where do I see the
ref codes" gets an honest answer: you do not configure them, you confirm them.
This turns "hope the two halves line up" into "see that they do."

## 5. Switching a study's mode is allowed — the guard is about the write side

Earlier framing held that flipping mode must be *prevented* because swoosh
recomputes all history and old respondents have no `vt`. That is too strong. The
**read side is additive**, and swoosh coalesces cleanly:

- `extractValue` (`inference_data.go`) runs every conf per respondent; a conf
  that finds nothing does `!ok → continue` — **skipped, not errored**. Only a
  real extraction error aborts.
- A thick-era respondent (inline metadata, no `vt`) satisfies a raw `gender`
  conf and skips a lookup `gender` conf. An encoded-era respondent (thin ref,
  only `vt`) skips the raw conf and satisfies the lookup. The eras **partition by
  presence of `vt`** — never both — so `addValue` never hits its conflict path,
  and both write the same `gender` column.
- The "unmapped/organic" bookkeeping does not drop anyone: `adAttributionOutcome`
  is a **count, not a failure** (`inference_data.go` comment: "organic and
  unmapped are counts, not failures … dropping those would turn a missing mapping
  row into missing survey data too").

So the invariant "`ad_table_lookup` is for new studies only" holds only if you
**replace** the read conf. **Keep the old raw conf and add the lookup**, and both
eras attribute.

Therefore, do **not** hard-prevent flipping. Instead:

1. **Add, don't replace.** When a study's write mode changes, the system
   **retains the prior era's read conf** and **adds** the new one. You can never
   drop a mapping that living respondents still need.
2. **Warn about the write-side cost, because that is the real one.** The ref is
   part of the creative (`COMPARED_AD`), so flipping `ref_mode` makes
   reconciliation see **every existing ad as drifted** and rewrite all of them:
   real spend, possible Meta re-review, ad learning-phase reset, and the live ad
   that reshared page-posts still point at changes under old respondents. That —
   not attribution loss — is what a flip warning is about.
3. **Residual: monitoring noise.** Once a study has a lookup conf, every
   thick-era respondent throws an `entityAdOrganic` "arrived with no ref token"
   count — not data loss, but it muddies the exact `unmapped`/`organic` signal
   that exists to catch real misconfigurations. Worth teaching the monitoring to
   scope that count to the encoded era.

Because there are no legacy WhatsApp/multi studies, the **only** flip that can
occur is a **Messenger study going thick → encoded**, one direction, opt-in.
WhatsApp and multi are born encoded and never flip.

## 6. Validation: make the wrong thing unsaveable

The incoherent states should **422 at save**, naming *both* sides, not warn hours
later in a cron log:

- encoded write with no matching read conf (or vice versa),
- a lookup on a non-`metadata` location (already refused in pydantic and
  `getRetrieveFunc`; keep),
- `ref_mode` contradicting an explicitly-set `include_metadata_in_ref` (already
  raised by `ref_mode_must_not_contradict_the_legacy_flag`; keep, though the UI
  should stop sending `include_metadata_in_ref` at all).

`thins_its_ref_without_reading_the_mapping` currently only warns. With thin
removed from the UI and encoded auto-wiring its read side (§7), the state it
warns about becomes unreachable for new studies; keep the warning as a backstop
for API-authored confs.

## 7. Auto-wire the read side

A stratified ad study attributes its respondents — you do not opt in. When a
study declares strata and fly destinations, the system should **generate the
read-side extraction confs from the strata already defined**, rather than making
the researcher re-declare each stratum variable as an `ad_table_lookup`
extraction by hand. The researcher already told the system the stratum variables;
asking again, in a different form, is the split that produces silent
half-configs. A study that wants to attribute on a variable it did *not*
stratify on remains a manual addition in Variables — an addition, not the common
path.

## 8. End state, in one paragraph

The dashboard offers two attribution choices — **encoded (default, all
channels)** and **thick (Messenger only, "legacy but useful")** — framed by what
they do to the researcher's data, never by the word `ref_mode`. The model keeps
`ref_mode: None → legacy` untouched for migration safety, and the UI writes an
explicit mode for every new conf, so `None` means exactly "pre-feature thick
Messenger." Editing an existing study preserves its stored mode; the UI default
applies only to new confs. Thin is deleted. Switching a Messenger study to
encoded is allowed — the system keeps the prior read conf and adds the new one,
and warns about the ad-rewrite cost, not about data loss. `ref_token` is shown as
a post-build confirmation surface, and the read-side extractions are generated
from the strata the researcher already declared.
