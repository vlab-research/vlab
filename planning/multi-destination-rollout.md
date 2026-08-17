# Multi-destination rollout plan

**Date:** 2026-08-17
**Status:** plan — the code is merged on `feature/multi-destination` and gated off
**Shareable version:** https://claude.ai/code/artifact/d4c55e8c-148c-4621-bf3c-94a007894e48

**Companion reading:**
- `documentation/multi-destination-ads.md` — the feature doc and the measurement procedure
- `planning/whatsapp-destination-model.md` — why multi is a third destination type
- `planning/ad-id-attribution.md` — the attribution design Phase 2 completes

---

## The three blockers

Each independently prevents a researcher from running a multi-destination study and
trusting the result. They are not sequential: two can be worked in parallel and one is
a decision rather than a build.

| # | Blocker | Kind | Blocks |
|---|---|---|---|
| 1 | The WhatsApp arm has never been observed | measurement | whether multi routes correctly at all |
| 2 | fly never stamps `ad_id` | engineering | attribution for any thin-ref study |
| 3 | `CONVERSATIONS` unavailable on the Virtual Lab Page | decision | configuring multi on that Page |

### Blocker 2 is newly confirmed and was not in the original brief

`grep -rn ad_id` over `replybot/lib`, `dean`, `message-worker`, `botserver` and
`devops/migrations` returns **nothing**. Meanwhile vlab's Go connector documents `AdID`
as "a first-class column on fly's responses view, resolved by fly at
conversation_started" (`inference/sources/fly/main.go:62-70`).

So vlab freezes `ad_attributions` rows and fly supplies no id to join them on. Worse,
the miss is invisible rather than merely absent: `adFields("")` returns `("", "")`, so
it is not even counted as `unmapped` — the bucket that exists to catch exactly this.

`include_metadata_in_ref` defaults **off** for both `FlyWhatsAppDestination` and
`FlyMultiDestination`. A default-configured study of either type therefore carries only
`form.<shortcode>`, routes correctly, and attributes nobody: every stratum counts zero
and the optimizer reallocates on empty data. That is the failure
`thins_its_ref_without_reading_the_mapping` warns about, and it currently only warns.

**Correction to an earlier claim:** single-destination WhatsApp was described as "usable
end to end". That holds for *routing*, which is measured. It does not hold for
*attribution* unless the study opts into full refs.

---

## Baseline: what is proven versus built

| Capability | Built | Evidence |
|---|---|---|
| Ad-set `destination_type` derivation | yes | measured against production confs |
| Two silent misroutes closed | yes | measured (fail at config time) |
| Messenger arm of a multi ad | yes | **measured** — ad `120254903561240150` |
| WhatsApp arm of a multi ad | yes | **unmeasured** — the gate |
| Single-destination WhatsApp routing | yes | measured |
| Attribution for thin-ref studies | **no** | — |
| Dashboard forms | yes | — |
| Page ↔ number chain check | **no** | — |
| Fallback-survey alerting | **no** | — |

---

## Phases

Dependency-ordered, not calendar-ordered. Phase 0 first; 1 and 2 in parallel; 5 needs
1–4.

### Phase 0 — Alert on fallback-survey arrivals *(do first)*

Every failure mode in this project ends the same way: a respondent silently starts
`FALLBACK_FORM` and looks like a completion. That is why VIR-19 ran four days and 1,770
users. `devops/alerts/templates/study-health.yaml` has a working alert framework and
nothing watching this.

This turns every risk below from a silent multi-day incident into a page, and is worth
doing whether or not multi ever ships.

**Exit:** a synthetic misroute in staging fires the alert; the production baseline rate
is known and written down.

### Phase 1 — Measure the WhatsApp arm *(parallel with 2)*

Procedure is written: `documentation/multi-destination-ads.md` §4, with an empty result
log. Run Procedure A first — `ctwa_probe.py --variant multi --multi-fallback whatsapp`
steers a preview click to the WhatsApp arm while leaving the ad set, the combined
welcome blob and the destination array byte-identical.

Record the compose box **before** sending; that observation is the measurement. If
ambiguous, escalate: Messenger logged out → second account with no Messenger history →
tiny live activation.

**Exit:** compose box holds `form.<shortcode>` verbatim (not Meta's default prefill);
referral carries `source_type: "ad"` and the exact ad id; arrival's form is not `305`.
Logged in §4.5 with the caveat that Procedure A measures the blob, not Meta's own arm
selection.

### Phase 2 — Make fly stamp the ad id *(parallel with 1; long pole)*

At `conversation_started`, resolve and persist the ad id — `referral.ad_id` on
Messenger, `referral.source_id` on WhatsApp — and expose it on the responses view the
connector already expects. Fix the classification in the same change so a missing id
counts as unmapped rather than vanishing.

**Exit:** a Messenger arrival and a WhatsApp arrival each produce a response row with
`ad_id` set; swoosh resolves both to their stratum; a thin-ref study produces the same
stratum counts as an equivalent full-ref one.

### Phase 3 — Settle the optimization-goal conflict *(decision)*

Two measured facts collide: the Virtual Lab Page cannot use `CONVERSATIONS` for CTWA (EU
privacy rules), and Meta's guide calls `CONVERSATIONS` mandatory for multi — yet this
repo measured a multi ad set accepting `LINK_CLICKS`.

Options: run multi on a Page without the EU restriction; relax the check to a warning on
the strength of the measured acceptance, accepting the cost-per-respondent tax of
optimising for clicks; or keep it strict and accept multi is unavailable on this Page.

**Exit:** decision recorded in `documentation/multi-destination-ads.md` §3, with the
reasoning.

### Phase 4 — Preflight the Page ↔ number chain

```
creative template object_story_spec.page_id
  → Page has a WhatsApp number linked          (Meta-side)
    → that number's phone_number_id
      → == credentials.key where entity='whatsapp_business'
```

Represented in neither repo. Break any link and the ad runs while the respondent's
message lands somewhere fly holds no credentials for. Reading the Meta-side half needs
App-Review-gated Page permissions, so assert the fly-side half and surface the Meta side
as an operator checklist rather than pretending to have verified it.

**Exit:** a study with a broken fly-side chain fails at config time; the Meta-side steps
exist as a followable checklist.

### Phase 5 — Enable, canary, then open up *(needs 1–4)*

Set `ADOPT_ENABLE_MULTI_DESTINATION` in `devops/values/<env>.yaml` and apply through
Helm — never imperatively — then restart the deployment, since pods do not reload env.

Staging first, then **one canary study** in production: tiny budget, narrow targeting,
watched daily. Watch not whether ads are created but whether both arms arrive, both
attribute to a stratum, and Phase 0's fallback rate stays flat.

**Exit:** the canary produces respondents on both channels, all resolving to strata, no
fallback arrivals attributable to it. Then drop the "not yet enabled" label from the
dashboard option.

---

## A shorter road, with a cost

Phase 2 is the long pole and can be skipped for a first study, because attribution has
two possible carriers and only one is broken.

**Fast path** — ship multi with `include_metadata_in_ref: true`. Stratum metadata rides
the ref on both arms, so attribution works with no fly changes. Needs Phases 0, 1, 3, 4
only. Cost: the WhatsApp arm's token sits in the respondent's compose box, visible and
editable, and every stratum value must survive fly's entry pattern. It is also the
opposite of what the ad-id design is for.

**Full path** — land Phase 2, keep the defaults, attribution comes from the frozen
mapping row. This is the design as intended, and it is also what makes thin-ref
Messenger and WhatsApp studies viable, so the work is not multi-specific.

Recommended: fast path for the canary if there is time pressure, but not as the default
configuration — the ethics of describing someone back to themselves before a survey
starts are why the default is off.

---

## Deferred

- **Instagram.** The destination-type vocabulary accommodates the
  `MESSAGING_INSTAGRAM_DIRECT_*` tokens; nothing else does. Nothing is known about what
  an Instagram Direct arrival carries, and fly has no normalizer, receiver or send path.
- **The `url_tags` decoding question.** One production event shows Meta decoding
  percent-escapes on the `url_tags` carrier but not the quick-reply one. Multi ships
  `url_tags` so it inherits the question, but it gates a separate change (D2), not this
  one.
- **Changing channel on a running study.** Structurally impossible — `destination_type`
  rides only on ad-set creates and ad sets are matched by name for a study's lifetime.
  Say it in the UI rather than engineering around it.
