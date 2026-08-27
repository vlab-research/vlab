# Runbook — fielding `vl-pulse-nigeria-smoke`, the encoded-ref end-to-end test

**Date:** 2026-08-27
**Status:** **Legs 0, 1 and 2 run (§0.5). Pass 1 written, NOT run. Pass 2 not
written in detail.**
**Study:** `vl-pulse-nigeria-smoke` — the study designed in
`planning/smoke-study-nigeria.md`. Its survey (`vlpulseng`) and study record
already exist in production; it has **no confs**, so §3 is where it gets built.
**Operator:** a human with a phone, dashboard access, and `kubectl` on `vprod`.
**Cost:** **pass 1 is free** — adopt creates the campaign `PAUSED` and nothing is
ever activated. **Pass 2 spends $10** and is a separate decision (§11).
**Companion docs:** `planning/smoke-study-nigeria.md` is the study design —
instrument, consent, payment, parameters. `planning/encoded-ref-probe-plan.md`
is the specification of the legs. `planning/ctwa-probe-runbook.md` is the idiom
this follows and the record of a probe run against live Meta ads on 2026-08-17;
several of its findings are reused here rather than re-measured.
`documentation/ad-attributions.md` is the mechanism.

## Two passes, and why they are not one

`smoke-study-nigeria.md` designs three arms — messenger, whatsapp, multi — at
$10 with ₦500 Reloadly incentives. It left open whether to field all three at
once. **They are split here, and Messenger goes first, alone and unpaid.**

Two measurements force it. A multi ad's WhatsApp arm was **never reachable by
preview** on 2026-08-17 — every attempt followed the single-valued
`MESSAGE_PAGE` CTA to Messenger (`ctwa-probe-runbook.md` decision row G, still
open). And WhatsApp is not a live transport (fly
`planning/multi-platform-plan.md`). So two of the three arms cannot be verified
without spending, and fielding all three together would put the one arm that
*can* be checked for free behind the two that cannot.

| | Pass 1 (§§3–9) | Pass 2 (§11) |
|---|---|---|
| Arms | Messenger only | + whatsapp, + multi |
| Campaign | stays `PAUSED` | activated |
| Respondents | you, via the ad preview | real, in Kwara |
| Cost | **zero** | $10 ad spend + ₦500/respondent |
| Proves | the whole attribution chain: write, format, carriers, decode, join | delivery, WhatsApp, Reloadly payment, the recontact list |

Pass 1 is the pre-flight the 2026-08-21 session promised and could not run.
Everything it proves is a variable pass 2 no longer has to debug while money is
moving.

---

## 0. What this test decides

Four questions. The first three are answered below; the fourth is what the
whole thing exists for.

| # | Question | Why it decides something |
|---|---|---|
| **0** | Does adopt write an `ad_attributions` row when it creates an ad? | The table has **zero rows**. Every later question assumes the write half works, and nothing distinguishes "healthy with nothing to do" from "never fires". |
| **1** | Does the replybot tag we *run* decode what adopt *mints*? | Two vendored reimplementations across a repo boundary, in two languages, with nothing detecting drift. |
| **2** | Does Meta deliver a base64url payload intact through all three carriers? | If Meta mangles it, the format changes and question 3 is void. |
| **3** | Does one real respondent's encoded ref reach `inference_data` as a declared variable? | The only question that proves the feature. Nothing has ever carried a real respondent. |

**The failure mode is silence, and that is the point.** A ref fly cannot decode
does not error — the respondent lands in `FALLBACK_FORM` (`305`, a real
researcher's live survey) and looks like a completion. A token that comes back
but joins to nothing does not error either; it is an *expected* arrival that
reports nothing. Neither shows up anywhere without someone looking.

### Already settled — do not re-test

Each verified on **2026-08-26** unless dated otherwise, and cited so the next
person can re-check rather than re-measure.

| Claim | Evidence |
|---|---|
| The deployed replybot decodes vlab's minted refs | `replybot-v0.0.221`, 37 assertions in fly's `ref-encoding-contract.test.js` over `adopt/adopt/ref_encoding_vectors.json`. See §0.5 leg 1. |
| replybot v0.0.221 runs in **both** `vprod` and `vstag` | `kubectl -n vprod`, `-n vstag`; and `versionReplybot` in fly's `devops/values/production.yaml` on `origin/main`. |
| adopt / swoosh in `vprod` | `v0.1.79` / `v0.1.11`, helm release `vlab` rev 137. |
| `ad_attributions` exists and holds **0** rows | `SELECT count(*) FROM ad_attributions` on `gbv-cockroachdb-0`. |
| The feature is inert | 0 of 719 destination confs carry `ref_mode`; 0 of 691 inference confs carry `mapping`. |
| Messenger is the only live transport | fly `planning/multi-platform-plan.md`. WhatsApp is not live, which is half the reason pass 1 is Messenger-only. |
| The dashboard exposes ref mode | `e7683333` (2026-08-24), `RefModeField.tsx` + `refMode.ts`, rendered by all five destination forms. The API-token path that blocked `vlpulseng` on 2026-08-21 is no longer needed. |
| `vlpulseng` and `vl-pulse-nigeria-smoke` exist, with **no confs** | queried 2026-08-27; `study_confs` returns 0 rows and there is no `study_state` row. |
| Preview clicks produce genuine referrals, with no activation, review or spend | Measured 2026-08-16, reconfirmed 2026-08-17 (`ctwa-probe-runbook.md` §0.5). |
| A failed fallback cannot cross researchers | fly `7232c3b7`: `formcentral/db.go:82` resolves a survey by the owner of the account the conversation is already on. |
| vlab **staging is unusable** | `toixo-staging.yaml` pins adopt `v0.0.106` and has no `migrations:` block. Do not try to run this there. |

---

## 0.5 Results

### Leg 0 — does the write half produce a row? **INDETERMINATE, with complete coverage.** **[measured 2026-08-26]**

Run: `adopt/scripts/write_path_probe.py`.

```
cutoff              2026-08-20T22:00:38+00:00
                    (adopt v0.1.78 prod values bump b94aafe3; helm rev 136)
studies with a conf 134
  ...actually read  105
  ...no campaign     10
  ...unreachable     29
ad_attributions     0 row(s) total
ads created since   0
```

**No study has created an ad on Meta since the write path reached production.**
So zero rows is exactly what a healthy path with nothing to do produces, and
the table cannot distinguish that from a path that never fires.

The 29 unreadable studies are not a hole. adopt touches a study only while
`start_date < now < end_date` (`recruitment_data.get_active_studies`), and
**every one of the 29 had finished recruiting before the cutoff** — so none
could have created an ad in the window whatever their ad account permits. The
script reports that distinction explicitly rather than quoting a bare
exclusion count.

Two facts about why this needed a script at all, both worth keeping:

- **The database cannot answer it.** adopt records nothing per instruction. The
  only trace of an ad create is a `logging.info` line in a cronjob pod
  Kubernetes keeps for three runs, and `adopt_reports` stores the optimiser's
  budget report, not the instruction list. The evidence had to come from Meta's
  own `created_time`.
- **Scope by campaign, never by ad account.** `ctwa_probe.py` creates ads by
  hand on `act_1342820622846299`, the same account the studies use. Those ads
  carry no provenance and *correctly* have no row. Counting them would report a
  broken write path on evidence of the probe working as designed.

**Consequence: leg 0 and leg 3 are one event.** Leg 3's ad is the first create
in the window, so §4 records leg 0's answer. It also means the probe **cannot**
use `ctwa_probe.py` to make the ad — a hand-made ad has no provenance and
writes no row, which would answer nothing.

The write path is otherwise covered by `test_ad_attributions.py` against a real
database with a fake Graph updater. The one seam no test reaches is the real
SDK's created-id return value, and that is precisely what §4 exercises.

### Leg 1 — the deploy contract. **PASSES against the deployed tag, and found two live drifts.** **[measured 2026-08-26]**

`adopt/adopt/ref_encoding_vectors.json` — 11 mint vectors, 11 must-reject
vectors, 11 WhatsApp entry vectors. vlab asserts it mints them
(`test_ref_encoding_contract.py`, 46 assertions); fly asserts the tag named by
`devops/values/production.yaml` decodes them
(`ref-encoding-contract.test.js`, 37 assertions, `replybot-v0.0.221`).

**Why it reads a git tag rather than the file next to it.** Measured in fly on
2026-08-26, minutes apart:

```
git show main:replybot/lib/typewheels/utils.js | grep -c decodeRecruitmentRef
  -> 0        the local main was five days stale
git show replybot-v0.0.221:.../utils.js        | grep -c decodeRecruitmentRef
  -> 3        the tag running in vprod AND vstag
grep -c RefDecodeError replybot/lib/errors.js  (on a live feature branch)
  -> 0        the decoder's error type is not there either
```

Same repository, same minute, three answers. Only the tag's answer is about
production. Verified negatively too: pointing the test at `replybot-v0.0.218`
fails 18 of 37, and fails first on a case worded as a *deploy* problem rather
than a *format* one.

**Drift 1 — adopt's vendored WhatsApp gate was two widenings behind.**
`test_marketing.WHATSAPP_ENTRY_REF` sat at `v0.0.219`'s shape while `v0.0.221`
ran:

| tag | shape |
|---|---|
| `v0.0.218` | `form.` must LEAD; alphabet `[A-Za-z0-9_-]` |
| `v0.0.219` | `form.` must LEAD; alphabet widened to accept `%XX` |
| **`v0.0.220`** | **the `form` *pair* may appear ANYWHERE in the pair list** |
| `v0.0.221` | unchanged; deployed |

The comment above that copy already read *"this copy went stale once already."*
It had gone stale twice. Both times in the safe direction — the copy was
*stricter* than production, so adopt refused refs fly would have accepted —
but that is a fact about the last two changes, not a property of the setup.
Fixed, and now pinned by the gate vectors.

**Drift 2 — a documented, "verified" claim had become false.**
`documentation/ad-attributions.md` recorded that `make_ref`'s output *"can
never match"* the WhatsApp gate, and that this was structural. The `v0.0.220`
widening removed it: `creative.<name>` is two tokens and every metadata entry
adds two more, so `form` always lands on a pair boundary. Measured on the
deployed tag, `creative.Smiling.form.mnchweek.gender.women` yields
`{form: mnchweek, creative: Smiling, gender: women}` — it now matches *always*
rather than never. Nothing is broken and `whatsapp_ref` should not change; what
changed is the reason it exists. Document corrected, and the two tests that
asserted the old claim rewritten to assert what is actually true.

### Leg 2 — do the carriers survive? **DEFERRED into §5, deliberately.** **[not measured]**

The plan proposed extending `ctwa_probe.py` to build an encoded creative and
read all three carriers back. That was descoped once §4 was settled: leg 3
already makes adopt build the real creative, and `ctwa_probe.py --read-back`
already prints `url_tags`, `quick_replies` and `autofill_message.content` off
any live ad. A second builder would measure a hand-made approximation of the
thing sitting next to it.

So leg 2 is **§5 of this runbook** — a read-back step against adopt's own ad,
before anything is clicked. Its result belongs in
`documentation/ad-attributions.md`, not in a test that reruns forever.

What is already known: dotted refs survive all three carriers intact, measured
2026-08-17 (`ctwa-probe-runbook.md` §0.5), and base64url's alphabet is a strict
subset of what those refs already carried. So this is expected to hold. Expected
is not measured.

### Leg 3 — one real arrival. **NOT RUN.**

§§3–8 below are pass 1: `vl-pulse-nigeria-smoke` with its Messenger arm only,
campaign paused, you as the respondent. Fill in §0.5 here when it is run.

§11 is pass 2 — the paid Kwara field test `smoke-study-nigeria.md` designs. It
is deliberately not written in step-by-step detail yet, because several of its
parameters depend on what pass 1 finds.

### Leg 4 — the web/app bare token. **DESCOPED. Say so out loud.**

A web or app destination in `ref_mode: "encoded"` interpolates a **bare** token
into `url_template`. Routing does not depend on it — the template already points
at the survey — so routing and attribution are **decoupled**, and a token that
fails to reach the survey platform produces a perfectly successful respondent
who is silently unattributed. There is no `FALLBACK_FORM` to make it visible and
no unmapped counter either, because an event with no token is an *expected*
arrival.

Testing it needs a real Typeform or Qualtrics with a hidden field wired to the
token. We do not have one. **Do not fake it.** Recorded as a stated limit in
`documentation/ad-attributions.md` rather than left to look like a capability.

---

## 1. Confounds this run is designed to exclude

Read this section. Every item is a way to get a **confidently wrong answer**
rather than a missing one.

### 1.1 The probe script cannot create the ad — adopt must

`ad_attributions` rows are written by `malaria.record_ad_attribution`, which
fires only on an `("ad", "create")` instruction carrying `provenance`. Only
`facebook/reconciliation.ad_dif` stamps provenance, and only adopt runs it.

An ad made with `ctwa_probe.py --mode create` is therefore **unattributable by
construction**: no row, no token in the table, and swoosh would report every
respondent from it as unmapped. Using the probe to make the ad would answer
leg 0 negatively for a reason that has nothing to do with adopt.

The probe script is still used here — for `--read-back`, `--preview` and
`--find-arrivals`. It just does not build the thing under test.

### 1.2 A decode failure under an encoded ref is TOTAL, not partial

This is the one genuinely new risk versus the 2026-08-17 run, and it is worth
stating before anyone clicks anything.

Under a dotted ref the shortcode is one pair among many: mangle a metadata
value and the respondent is mis-attributed but still routed. Under an encoded
ref, `encode_recruitment_ref` packs shortcode **and** token into one payload, so
fly's decode yields **both or neither**. Neither means `md.form` is unset, and
`getMetadata` falls through to `FALLBACK_FORM` — `305`, a real researcher's
live survey.

That is *loud* rather than silent, which is the design working. It is still a
real person landing in someone else's study, so:

**Pre-flight before clicking (§6.0): run the ad's actual minted ref through the
actual deployed decoder.** Leg 1 proves the tag decodes the *contract vectors*;
this proves it decodes *this ad's ref*. They are not the same claim — the
shortcode is researcher-chosen text and none of the vectors is `vlpulseng`.

### 1.3 The first adopt run creates only the campaign

`marketing.update_instructions_for_campaign` returns **early** when the campaign
does not exist yet:

```python
except StateNameError as e:
    logging.info(f"Could not find campaign with name {campaign_name}. Creating.")
    return [create_campaign(campaign_name, study.recruitment.objective)]
```

So run 1 creates the campaign and stops. Adsets and ads come on run 2.
`vlab-adopt-ads` is `30 */2 * * *`, so **budget up to ~4.5 hours** from saving
the study to an ad existing. An absent ad after one cycle is not a finding.

### 1.4 Why nothing spends, stated precisely

Three different statuses, and only the first one matters:

| Object | Status at create | Where |
|---|---|---|
| campaign | **`PAUSED`** | `marketing.create_campaign`, `marketing.py:1244` |
| ad set | `ACTIVE` if budget > 0, else `PAUSED` | `marketing.adset_instructions`, `:1216` |
| ad | **`ACTIVE`**, always | `marketing.adset_instructions`, `:1236` |

An `ACTIVE` ad inside a `PAUSED` campaign does not deliver. **The containment is
the campaign, and it is the only thing standing between this run and real
spend.** Do not activate it, and do not let the dashboard's Optimize step
activate it. Check it is still paused before you click (§6.0) and again at
cleanup (§9).

### 1.5 The ad set's 48-hour window

`ADSET_HOURS = 48`, so the ad set's `end_time` is 48h after creation. Whether an
expired ad set still previews is **not verified** (`ctwa-probe-runbook.md` §9
item 3, still open). Click inside the window; if you miss it, wait for the next
adopt run to rebuild rather than debugging the preview.

### 1.6 fly's no-retake rule makes an *absent* survey start meaningless

`machine.js:297-300`: if the referral's form is already in `state.forms`, the
referral is a no-op. The tester's PSID has walked `flysmoke` before, and will
have walked `vlpulseng` after the first attempt — so this bites on any re-run.

So **the raw row in `chatroach.messages` is the measurement**, not whether a
survey visibly starts. Scribble writes `messages` straight off the Kafka topic,
independently of the machine. Clear state first anyway (§3.6) so the end-to-end
half is observable.

### 1.7 Preview clicks may never fire the `url_tags` carrier

On 2026-08-17 **no top-level `OPEN_THREAD` referral fired on either Messenger
arrival** — both control and multi arrived solely via
`message.quick_reply.payload`. That matches the measured 68% majority pattern
rather than being obviously preview-specific, so it is not established that
previews suppress it.

For this run it matters less than it did there: both Messenger carriers carry
the **same** `r.<payload>` string (`create_creative`'s Messenger branch passes
one `ref` to both `make_welcome_message` and `url_tags`), so either one arriving
proves the decode. But if only the quick-reply carrier fires, **`url_tags` stays
unmeasured for encoded refs**, exactly as it stayed unmeasured for dotted ones.
Record which carrier fired; do not silently generalise from one.

### 1.8 `messages` dedupes on content hash, and has no timestamp index

`PRIMARY KEY (hsh, userid)` with `hsh = fnv64a(content)`, inserted
`ON CONFLICT DO NOTHING`. Two byte-identical webhooks collapse into one row —
if you click twice and see one row, that is why.

The table is ~101M rows and its only indexes are the primary key and
`(userid, timestamp)`. **Always query by `userid`.** A bare `content LIKE` or a
`WHERE timestamp > …` is a full scan taking minutes. Get the `userid` from
`states` first (§7.1).

### 1.9 A returning Messenger thread may not render the welcome screen

Meta shows the welcome screen — and therefore the quick-reply button — on a
**new** thread. PSID `1989430067808669` already has a thread with the Virtual
Lab page. If no button appears, that is §1.9, not a finding. §3.6's reset clears
`state.forms`, which was enough on 2026-08-17; if the button is still missing,
retry from an account with no history on page `1855355231229529`.

---

## 2. Preconditions

| Thing | Value | How it is obtained |
|---|---|---|
| Ad account | `act_1342820622846299` (Virtual Lab — USD) | the account the probe and ECD Diagnostic both use |
| Facebook Page | `1855355231229529` (Virtual Lab) | probe default |
| Study | **`vl-pulse-nigeria-smoke`** (`e460dfde-a010-49b3-b012-d48dbaadb34b`) | already exists, created 2026-08-21 18:54 UTC, with zero confs |
| Org | `031963f3-0a38-4ca5-9714-0c9012f9ac91` | **not** ECD Diagnostic's org (`3bc602fc-…`). This constrains §3.1 — see there. |
| Study owner | `auth0|62470aac9bf338006971a7d2` | holds `Facebook` (facebook), `toixo` (fly) and `virtual-lab-vlab` (facebook_ad_user) credentials. Verified 2026-08-27. |
| Survey shortcode | **`vlpulseng`** (`VL Pulse Nigeria - Smoke`, created 2026-08-21 16:24 UTC) | already synced into `chatroach.surveys`. A nonexistent shortcode routes to `FALLBACK_FORM` = `305`, someone else's live survey. |
| Source study to copy from | **`vapefree-evaluation-aim3`** | same org, same ad account, one variable with two levels, a Messenger fly destination, fly credential `toixo`, and templates confirmed alive 2026-08-27. §3.1 says why not `ecd-diagnostic`. |
| Reloadly credentials key | `vlab`, on `nandanmarkrao@gmail.com` | the study must be owned by that account or the payment credential will not resolve. **Pass 1 never reaches a payment**, so this only gates §11. |
| Meta access token | — | read from the prod `credentials` table by the scripts; never passed on argv |
| Python | `adopt/.venv` | `cd adopt && poetry install` |
| Cluster access | `kubectl` context on `vprod` | needed by every script and every SQL step |
| A phone | — | Messenger, logged in |

Cron cadence, all in `vprod`:

| Job | Schedule | What it does for this run |
|---|---|---|
| `vlab-adopt-ads` | `30 */2 * * *` | creates the campaign, then the adset + ad |
| `vlab-source-fly` | `10 * * * *` | pulls fly responses into `inference_data_events` |
| `vlab-swoosh` | `30 * * * *` | joins the token and writes `inference_data` |

All probe commands run from `adopt/` as `.venv/bin/python scripts/…`.

---

## 3. Build the study — all of this is the dashboard

**Pass 1.** Nothing in this section is code, and that is the point of the whole
design: a researcher does it. It was not true on 2026-08-21, when ref mode was
API-only and `vlpulseng` stalled needing an Auth0 bearer token. The dashboard
control shipped as `e7683333` on 2026-08-24.

The study **already exists** — `vl-pulse-nigeria-smoke`, created 2026-08-21,
with zero confs. Open it and configure it; do not create a second one.

### 3.1 Copy a working configuration

On the **Initialize** step, select **`vapefree-evaluation-aim3`** and click
*Initialize Values*.

That copies every conf except `general`, which is what makes this cheap: the
variables arrive with valid `facebook_targeting` and real `template_adset` /
`template_campaign` ids on the account. Building those by hand is most of the
work of a new study and none of what this test is about.

**Not ECD Diagnostic**, and this is not a preference. `Initialize` lists the
studies in the **current org**, and `vl-pulse-nigeria-smoke` is in org
`031963f3-…` while `ecd-diagnostic` and `girl-effect` are in `3bc602fc-…` under
a different owner. ECD will not appear in the dropdown. Its `data_sources` conf
would not have worked either: it names fly credential `Fly`, and this study's
owner holds `toixo`.

`vapefree-evaluation-aim3` was chosen over the other same-org candidates because
it is the **smallest** — one variable (`Gender`), two levels — so §3.5's trim to
a single stratum is a two-click edit rather than a cull. Its fly source already
uses `toixo`, its destination is already a Messenger fly destination, and its
templates were confirmed alive on 2026-08-27:

```
adset     120227643423940150  'Gender - Men'          CAMPAIGN_PAUSED
campaign  120227642396520150  'Templates - VapeFree'  PAUSED
```

`shujaaz-free2choose-digital-evaluation` (templates also alive) is the fallback
if vapefree's have been deleted by the time you read this — it is a real
Messenger study on the same account, just with five levels to trim instead of
two.

> Initialize **overwrites** anything already configured on this study. It has no
> confs today, so nothing is at risk — but do it first, not after editing.

### 3.2 General

Ad account `1342820622846299`. The study must stay owned by
**`nandanmarkrao@gmail.com`** — that is where the Reloadly `vlab` key lives, and
pass 2 cannot pay anyone from another account. Pass 1 never reaches a payment,
so this costs nothing to get right now and is expensive to discover later.

### 3.3 Recruitment

- **`ad_campaign_name`: `vl-pulse-nigeria-smoke`** — must be unique on the
  account; it is what the ad lives under and what §9 deletes.
- **start date in the past, end date a few days out.** adopt only touches a
  study where `start_date < now < end_date`, and this study currently has **no
  `study_state` row at all** (both dates NULL). Get this wrong and nothing
  happens, silently, forever — it is exactly what has been true since
  2026-08-21.
- `destination_type`: `MESSENGER`.
- Budget: leave the copied values for now. Nothing can spend in pass 1 (§1.4);
  a low `min_budget` is belt-and-braces, not the control. §11 sets the real $10.

### 3.4 Destinations — the write side

One Messenger destination. The whatsapp and multi arms of
`smoke-study-nigeria.md` are **pass 2** — do not add them yet (see *Two passes*
above).

- `initial_shortcode`: **`vlpulseng`**
- welcome message and button text: anything; the button label is what you tap.
- **Ref mode: "Looked up afterwards, from the ad-attributions export."**

That last one is the whole write half. The words `ref_mode` and `encoded` never
appear on screen — the control labels by consequence
(`forms/destinations/refMode.ts`). The other option, *"In the data itself —
gender and region arrive as columns,"* is the historical behaviour.

Saving a *change* of mode on an existing destination raises a warning about
rewriting every ad in the study. On a new study there is nothing to rewrite.

### 3.5 Strata, and the variable the ad is frozen with

vapefree's copy gives you two strata (`Gender:Men`, `Gender:Women`), six
creatives each. Three edits:

1. **Delete `Gender:Women`.** One stratum × one creative × one destination =
   exactly one ad, which is what makes §4 and §7 unambiguous.
2. **Trim `Gender:Men` to ONE creative.** It arrives with six (`RC34 Ad 4`,
   `RC34 Ad 2 v2`, …); each one is another ad and another `ad_attributions`
   row. Delete the rest from Creatives too, or the conf references creatives
   the stratum no longer uses.
3. **Clear `excluded_audiences`.** It arrives holding
   `["VapeFree Evaluation Aim3 respondents"]` — another study's custom
   audience. Leaving it makes this study's ad set depend on an audience it does
   not own.

**Simplify `question_targeting`.** vapefree's is

```
and( equal(variable Gender, constant "Men"),
     answered(variable would_like) )
```

`would_like` is a vapefree survey question; `vlpulseng` has no such field, so
that clause can never match. Drop it and keep only
`equal(variable Gender, constant "Men")`.

Two reasons, and the second is the one that matters. A predicate naming a
variable nothing supplies makes `missing_targeting_variables` warn on every
reconciliation run, which is noise you will then have to explain away. And
`Gender` is exactly the variable §3.6's lookup conf produces **out of the ad
table** — so keeping that clause and nothing else means the stratum matches if
and only if the whole encoded mechanism worked. It turns the stratum count into
a second, independent read on the same question §7.4 asks.

`smoke-study-nigeria.md`'s Kwara targeting matters in pass 2, when delivery is
real. In pass 1 nothing is delivered, so leave vapefree's US/18–25/Android
targeting alone rather than spending time on targeting that cannot be
exercised — it is a valid `facebook_targeting` block, which is all adopt needs.

The stratum's `metadata` is `{"Gender": "Men"}`. **That is the key §3.6's lookup
conf pulls**, and it must be a key the ad's frozen `ad_attributions.metadata`
blob carries — §4 checks exactly that.

### 3.6 Data Extraction — the read side

vapefree's copy arrives with two confs under its fly source, and **both are
wrong for us**:

```
{location: "variable", key: "would_like", name: "would_like"}   <- a field vlpulseng does not have
{location: "metadata", key: "Gender",     name: "Gender"}       <- a RAW read of an inline ref
```

The second is the interesting one: it is the *thick-ref* way of reading exactly
the variable we are about to read through the ad table. Under
`ref_mode: "encoded"` the ref no longer carries `Gender` inline, so that conf
finds nothing and is skipped — harmless, but it proves nothing. Replace it.

| Field | Value | Means |
|---|---|---|
| Location | **Metadata** | where the value is |
| Mapping | **"Ad (which ad recruited them)"** | the value read is a *token*; look it up |
| Key | **`vt`** | the metadata key holding the token — fly's convention |
| Name | **`Gender`** | the stratum variable to pull off the frozen row, *and* what to call the output. Capital G — it must match `stratum.metadata`'s key exactly. |

Delete the `would_like` conf. Optionally add one raw conf reading the survey's
own `gender` field (`location: variable, key: gender, name: gender`) — lowercase,
so it cannot collide — which gives you what the respondent *said* next to what
the ad *targeted*. Not required, and not part of any decision below.

**Key and name mean something different here than they do for a raw read**, and
getting them backwards is the easy mistake. Under `ad_table_lookup`, `key` is
where the **token** is and `name` is which **stratum variable** to pull.

Cross-check: the study's `question_targeting` predicate must match on the same
variable, or `missing_targeting_variables` warns and the stratum counts zero for
an unrelated reason.

### 3.7 Data Sources

One fly source. From vapefree's copy, change **only** `survey_name`:

| Field | Value |
|---|---|
| source | `fly` |
| name | `FLy` — **leave it exactly as copied, typo and all** |
| credentials_key | `toixo` — this study's owner has no credential named `Fly` |
| config.survey_name | **`VL Pulse Nigeria - Smoke`** (was `Washington University VapeFree`) |

The name looks like a typo because it is one, and it is load-bearing:
`inference_data` is a map **keyed by the data source's name**
(`{"data_sources": {"FLy": {"extraction_confs": [...]}}}`). Rename the source
without renaming the key and the study has a source with no extraction confs
and a set of confs attached to a source that does not exist — which produces no
variables, silently, and looks exactly like a broken lookup.

### 3.7b What NOT to configure in pass 1

The `vlpulseng` Typeform is already Reloadly-shaped — `payment:reloadly`, key
`vlab`, with the operator selector. Leave it alone. Pass 1 never completes the
survey (§3.8's warning), so the payment branch is never reached and no airtime
moves. Do not "test" the payment by walking the form to the end.

### 3.8 Clear your own Messenger state

Open `m.me/1855355231229529?ref=form.reset` on the phone you will use.
`REPLYBOT_RESET_SHORTCODE` is `reset` in production, and a `RESET` rebuilds from
`_initialState()` — `{state: 'START', qa: [], forms: []}` — so §1.6's no-retake
rule stops applying.

> **Do not walk `vlpulseng` to the end.** It is six questions and then a
> **live Reloadly payout** of ₦500 to whatever number you type. You need the
> *first* message only — enough to see which survey started. Completing it in
> pass 1 spends real money outside the $10 that pass 2 accounts for, and pollutes
> the study's own respondent counts before it has fielded.

---

## 4. Let adopt create the ad — and this answers leg 0

Wait for `vlab-adopt-ads`. Expect **two** cycles (§1.3): campaign first, then
adset + ad. Up to ~4.5 hours.

```bash
kubectl -n vprod get pods | grep vlab-adopt-ads
kubectl -n vprod logs <newest-pod> | grep -E "encoded-ref-probe|Executing: (ad|campaign)/|provenance"
```

What the log should say across the two runs:

```
Got N active studies to update
Updating Encoded Ref Probe
Could not find campaign with name encoded-ref-probe. Creating.   # run 1
Executing: campaign/create ...
...
Executing: adset/create ...                                       # run 2
Executing: ad/create ...
```

Then, the measurement:

```sql
SELECT ad_id, network, study_id, stratum_id, creative_name,
       shortcode, ref_token, resolved_from, metadata, created
  FROM ad_attributions
 WHERE study_id = '<study uuid>';
```

or, for the whole picture including what Meta says:

```bash
.venv/bin/python scripts/write_path_probe.py --study encoded-ref-probe
```

**Leg 0's answer is here:**

| Observation | Verdict |
|---|---|
| an ad exists on Meta **and** a row exists, `ref_token` non-NULL | write half **works**. Record the ad id and the token. |
| an ad exists, **no row** | write half **broken**. `record_ad_attribution` is not firing, or provenance is not reaching the create instruction. **Stop.** Everything downstream is moot; §6 onward would measure nothing. |
| an ad exists, row exists, **`ref_token` is NULL** | the destination's mode is not `encoded`. §3.4 did not save. Fix and wait for the next run — the ad will be rewritten, not recreated. |
| no ad after two cycles | not a finding yet. Check the study is active (§3.3), then read the adopt log for an exception. |

Also check the frozen blob carries what you expect:

```sql
SELECT metadata FROM ad_attributions WHERE study_id = '<uuid>';
-- expect {"creative": "<creative name>", "form": "vlpulseng", "gender": "women", ...}
```

`creative` and `form` must both be there. Their absence is the trap
`documentation/ad-attributions.md` calls invariant 1 — a blob built from
`stratum.metadata` instead of `creative_metadata` silently loses both, every
lookup resolves to nothing, and every stratum counts zero.

---

## 5. Read the carriers back — this is leg 2

**Before clicking anything.**

```bash
.venv/bin/python scripts/ctwa_probe.py --read-back <AD_ID>
```

Record, byte for byte:

| Carrier | Where in the output | Reaches |
|---|---|---|
| `url_tags` | `url_tags present: 'ref=r.…'` | Messenger `referral.ref` (~32% of entrants) |
| quick-reply payload | `page_welcome_message @ object_story_spec.link_data`, `quick_replies` | Messenger (~68%, their only carrier) |
| `autofill_message.content` | same blob | WhatsApp only — **absent here**, and correctly so: this is a Messenger destination |

Compare each against what adopt should have minted:

```bash
.venv/bin/python - <<'PY'
from adopt.ref_encoding import encoded_ref
print(encoded_ref("vlpulseng", "<ref_token from the row>"))
PY
```

All Messenger carriers must equal that string exactly — `create_creative`'s
Messenger branch passes **one** `ref` to both, and any difference means one ad
describing two different people depending on how they tapped it.

**What this measures:** whether Meta stores base64url intact. It is API
acceptance only; delivery is §6. Write the result into
`documentation/ad-attributions.md` — it is a one-shot fact about Meta, not
something to re-assert forever.

---

## 6. Click it

### 6.0 Pre-flight — three checks, none optional

```bash
# 1. the campaign is still PAUSED. This is the only thing preventing spend.
.venv/bin/python scripts/ctwa_probe.py --list-ads <CAMPAIGN_ID>

# 2. THIS ad's ref decodes under THE DEPLOYED TAG. Leg 1 proved the tag decodes
#    the contract vectors; none of them is `vlpulseng`. §1.2.
cd /path/to/fly
TAG="replybot-$(grep -m1 '^versionReplybot' devops/values/production.yaml | sed 's/.* //')"
D=$(mktemp -d); mkdir -p "$D/lib/typewheels"
git show "$TAG:replybot/lib/typewheels/utils.js"  > "$D/lib/typewheels/utils.js"
git show "$TAG:replybot/lib/errors.js"            > "$D/lib/errors.js"
ln -s "$PWD/replybot/node_modules" "$D/node_modules"
node -e "console.log(require('$D/lib/typewheels/utils').decodeRecruitmentRef('<payload after r.>'))"
# expect { form: 'vlpulseng', token: '<the ref_token from the row>' }
rm -rf "$D"
```

3. Your Messenger state is cleared (§3.8).

If the decode does not print exactly that, **do not click**. A respondent —
you — would land in survey `305`.

### 6.1 The click

```bash
.venv/bin/python scripts/ctwa_probe.py --preview <AD_ID>
```

Open it **on the phone**. Meta mints a fresh link per call; any works.

Everything here is rendered client-side and **will not appear in any database**.
Screenshot it or it is gone.

Record, in order:

1. Whether a welcome screen with a button appears, and the button's label. If
   not, see §1.9 before concluding anything.
2. Tap it. Record what comes back and how long it takes. **An absent or slow
   reply is not a result** — on 2026-08-17 outbound delivery lagged by minutes
   because `vlab-prod-message-worker` was ~444 messages behind. The inbound
   referral lands in `chatroach.messages` immediately and independently. Read
   the database; do not wait on the phone.
3. Whether the first message is `vlpulseng`'s. Its first field is **`consent_1`**
   — *"We are a group of researchers at Virtual Lab conducting a study…"* — not
   a question. `age` ("How old are you?") is the fifth field, after two more
   consent screens and a `start` prompt. Anything else means `FALLBACK_FORM`.
   **Stop at the first message**; see §3.8.

---

## 7. Read the result out of the database

```bash
kubectl -n vprod port-forward svc/gbv-cockroachdb-public 26257:26257 &
psql "postgres://root@localhost:26257/chatroach?sslmode=disable"
```

The `postgres://` scheme is required; `cockroachdb://` fails against libpq.

### 7.1 Find yourself, and where fly routed you

```sql
SELECT userid, pageid, platform, current_form, current_state, updated
  FROM states
 WHERE pageid = '1855355231229529'
   AND updated > now() - INTERVAL '2 hours'
 ORDER BY updated DESC;
```

`states` is ~1M rows and cheap. `current_form = '305'` means `FALLBACK_FORM` —
the ref did not survive. Note your PSID; §1.8 means every later query needs it.

Or: `.venv/bin/python scripts/ctwa_probe.py --find-arrivals --minutes 120`

### 7.2 Which carrier delivered, and what it carried

```sql
SELECT timestamp,
       content::jsonb -> 'referral' ->> 'source'                AS ref_source,
       content::jsonb -> 'referral' ->> 'type'                  AS ref_type,
       content::jsonb -> 'referral' ->> 'ref'                   AS top_level_ref,
       content::jsonb -> 'referral' ->> 'ad_id'                 AS ad_id,
       content::jsonb -> 'message' -> 'quick_reply' ->> 'payload' AS quick_reply_payload
  FROM messages
 WHERE userid = '<YOUR_PSID>'
   AND timestamp > now() - INTERVAL '2 hours'
   AND content LIKE '%"source":"messenger"%'
   AND content LIKE '%referral%'
 ORDER BY timestamp;
```

The two `LIKE` prefilters are not decoration: at least one production row fails
`content::jsonb` outright, so any query casting `content` over a wide window
must narrow first.

The two carriers arrive as **separate rows**:

- `top_level_ref` non-null with `ref_source = ADS`, `ref_type = OPEN_THREAD` —
  the `url_tags` carrier. May not fire at all (§1.7).
- `quick_reply_payload` containing `{"referral": {"ref": "r.…"}}` — the
  welcome-message carrier.

Whichever fired must carry **exactly** the `r.<payload>` from §5.

### 7.3 The decode

```sql
SELECT userid, current_form, current_state, updated,
       current_state::jsonb -> 'md' AS md
  FROM states
 WHERE userid = '<YOUR_PSID>'
 ORDER BY updated DESC LIMIT 1;
```

Expect `md.form = "vlpulseng"` and **`md.vt` = the `ref_token` from §4's row**,
with **no `md.r`** — it is consumed by the decode branch and must never survive
half-parsed.

### 7.4 The join

Back on the `vlab` database. `vlab-source-fly` runs at `:10` and `vlab-swoosh`
at `:30`, so allow one full hour.

```sql
-- the event carries the token in metadata
SELECT data->>'user_id', data->'user_metadata'->>'vt', data->>'ad_id'
  FROM inference_data_events
 WHERE study_id = '<uuid>'
 ORDER BY created DESC LIMIT 5;

-- swoosh emitted the declared variable
SELECT * FROM inference_data
 WHERE study_id = '<uuid>'
 ORDER BY created DESC LIMIT 5;

-- and reported nothing, which is the pass condition
SELECT event_type, severity, message, details, occurred_at
  FROM study_run_events
 WHERE study_id = '<uuid>'
   AND occurred_at > now() - INTERVAL '3 hours'
 ORDER BY occurred_at DESC;
```

An `extraction_error` at severity `error` naming `ref_token` is the **unmapped**
outcome: a token arrived and resolved to no row. That is always a bug.

---

## 8. Decision table

Written **before** the run so the conclusion is not reasoned backwards from
whatever happens.

| # | Observation | What it means | Consequence |
|---|---|---|---|
| **A** | §4: ad exists on Meta, **no `ad_attributions` row** | The write half never fires in production, despite `test_ad_attributions.py` passing against a real database. The untested seam — the real SDK's created-id return — is where it breaks. | **Stop.** Fix before anything else. Every encoded study built until then mints ads it cannot attribute, permanently: there is no backfill path. |
| **B** | §5: a carrier's string ≠ the minted ref | Meta mangles base64url, or the carriers disagree. | The format changes. Legs 3+ are void. Record exactly which carrier and how it differs — this is the finding the whole encoding rests on. |
| **C** | §6: no welcome button, **and** §7.2 shows no `quick_reply_payload` row | Either the returning-thread effect (§1.9) or a delivery change. | **Not a finding.** Inconclusive. Retry from a Messenger account with no history on page `1855355231229529`. |
| **D** | §7.1: `current_form = '305'` | The ref reached fly and fly could not decode it. Under an encoded ref this is total (§1.2). | The deploy contract passed and production still failed — which would mean the tag running is not the tag `production.yaml` names. Check the actual pod image, not the values file. |
| **E** | §7.3: `md.form = vlpulseng`, **`md.vt` absent** | The ref was dotted, not encoded — the ad shipped `ref_mode: "metadata"`. | §3.4 did not save, or the ad predates the save. Not a decode failure. Check `ref_token` on the row and the carrier string from §5. |
| **F** | §7.3 correct, §7.4 emits **`extraction_error` / `ref_token`** | The token round-tripped and joined to nothing. | The mapping row and the minted token disagree — the one thing `ad_ref_token` exists to prevent. Compare the row's `ref_token` against `md.vt` byte for byte; suspect quoting (`metadataToken` unquotes a JSON string). |
| **G** | §7.3 correct, §7.4 emits nothing **and** `inference_data` has no row | The event never reached swoosh, or the conf did not name the variable. | Check `inference_data_events` first (§7.4). If the event is there, the lookup conf's `name` does not match a key in the frozen blob — which is deliberately *not* counted as unmapped. |
| **H** | §7.4: `inference_data` carries the declared variable for your user | **Everything works.** Write path, format, carriers, decode, join. | The feature is proven end to end for Messenger. Record it in `documentation/ad-attributions.md` and in §0.5 above. WhatsApp repeats this walk once it is a live transport. |
| **I** | H, but only `quick_reply_payload` fired — no `top_level_ref` | The 68% carrier is proven; the 32% `url_tags` carrier is not. | Same as 2026-08-17 (§1.7). **Record it as unmeasured, not as working.** It is the carrier that would still route if the button were ever lost. |

**Two things worth recording whatever happens**, because they are cheap now and
expensive later:

- Which carriers fired, and whether `url_tags` ever populates `referral.ref` for
  an encoded ref. Never measured, on either format.
- Whether the ad set's 48h window had lapsed at click time (§1.5) — one
  observation either way retires `ctwa-probe-runbook.md` §9 item 3.

---

## 9. Cleanup — the same day

The campaign is `PAUSED` and cannot spend, but a paused campaign on a live ad
account is one mis-click from recruiting real people into a live survey that
pays ₦500 a head.

**Skip this only if pass 2 is starting immediately.** If §11 is going ahead
today, leave the campaign in place and go straight there — deleting and
recreating it costs an adopt cycle and a new set of ad ids for no benefit. If
pass 2 is days away or undecided, clean up.

1. **Set the study's `end_date` to the past**, so adopt stops touching it. Do
   this *first* — deleting the campaign while the study is still active means
   the next adopt run recreates it (§1.3).
2. Delete the campaign:

```bash
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign <CAMPAIGN_ID>
.venv/bin/python scripts/ctwa_probe.py --list-ads <CAMPAIGN_ID>   # expect empty or an error
pkill -f 'kubectl.*port-forward'
```

3. **Leave the `ad_attributions` row.** The table is append-only by design and a
   row must outlive its ad — respondents keep arriving from deleted ads. It is
   also the evidence for §0.5.
4. **Leave the survey and the study record in place.** Pass 2 (§11) reuses both.
   Only the campaign and the confs' dates change between passes.

---

## 10. Things that cannot be determined without running this

Marked so they are not mistaken for oversights.

1. **Whether the real Facebook SDK returns a created id that
   `update.created_id` can read.** Every test uses a fake updater. This is the
   single seam leg 0 could not reach, and decision row **A** is what it looks
   like if it fails.
2. **Whether a preview click on an ad inside a PAUSED campaign produces a
   referral at all.** The 2026-08-17 run previewed PAUSED *ads*, in campaigns
   the probe had also created paused — so the precedent is good but not
   identical: those campaigns were built by the probe, this one by adopt.
3. **Whether `url_tags` populates `referral.ref` for an encoded ref.** Open for
   dotted refs too (`ctwa-probe-runbook.md` §9 item 4). §1.7.
4. **Whether the 48h ad-set window affects previewing.** §1.5.
5. **Whether `(platform, account_id, user_id)` threading changes the shape of
   `User.ID` reaching swoosh** (`encoded-ref-probe-plan.md` §4). Rows are being
   stamped with `account_id` gradually right now. If a respondent's id shape
   shifts mid-study, swoosh sees two people where there is one — and §7.4's
   step depends on the answer. Check the `inference_data_events` rows in §7.4
   for which shape yours arrived with.

---

## 11. Pass 2 — the paid Kwara field test

**A separate decision, taken after pass 1 reports.** This is the study
`planning/smoke-study-nigeria.md` designs: $10 of ad spend, ₦500 Reloadly
airtime per respondent, `max_sample: 10` per arm across messenger, whatsapp and
multi. Not written in step-by-step detail here, because three of its parameters
depend on what pass 1 finds — which carriers fired, whether `url_tags` produced
a top-level referral, and whether the frozen blob carried every key the lookup
conf asks for.

What changes from pass 1:

| | Change | Why it is not free |
|---|---|---|
| Destinations | add a `whatsapp` and a `multi` destination, both `ref_mode: encoded` | a stratum may not mix channels, so this is three strata, three ads, three distinct `ref_token`s |
| Strata | restore Kwara targeting and `max_sample: 10` per arm | targeting only matters once delivery is real |
| Recruitment | the real $10 budget | |
| Campaign | **activate it** | this is the irreversible step: real spend, and Meta ad review |
| Survey | respondents complete it | each completion is a live ₦500 Reloadly payout |

### What pass 1 does not de-risk

Say these out loud before spending, because pass 1 proves none of them:

1. **The WhatsApp and multi arms cannot be preview-verified.** On 2026-08-17
   every preview of a multi ad followed `MESSAGE_PAGE` to Messenger and the
   WhatsApp arm was never reached (row **G**, still open). Their first real test
   is a paying respondent.
2. **A WhatsApp decode failure is silent and lands in someone else's survey.**
   `FALLBACK_FORM` is `305`, a real researcher's live study.
   `RecruitmentAdArrivalsInFallback` fires at ≥2 such arrivals in an hour —
   watch it from the first impression, not at the end of the day.
3. **The Reloadly operator string is an exact match.** `go-reloadly`'s
   `SearchOperator` does `op.Name == name` against the NG catalog; a wrong
   string returns `OPERATOR_NOT_FOUND`. `MTN Nigeria` and `Glo Nigeria` are
   verified exact (they are what `bauchiendpayENG` pays with).
   `Airtel Nigeria` and `9mobile Nigeria` are **not verified**. A wrong string
   is a handled failure, not vanished money — the form's `reloadly_er` branch
   fires and the respondent sees the error — but it is a respondent who
   answered and did not get paid.
4. **`thins_its_ref_without_reading_the_mapping` only warns.** It will not stop
   a save or a run. If a destination ends up thin with no lookup conf, every
   stratum counts zero and the optimizer reallocates on empty data, silently.
   Check §4's `ad_attributions` rows have non-NULL `ref_token`s — one per arm,
   all distinct — **before** activating. That check is the whole reason pass 1
   exists.
5. **Consent flags 1–3 in `smoke-study-nigeria.md` are unresolved.** No IRB
   claim, the platform-caveats screen must stay channel-neutral across three
   arms, and the stated duration and prize must match the built form. An
   inaccurate consent is the easiest thing to ship by accident when adapting
   one.

### The gate

Do not activate until §4 shows **three** `ad_attributions` rows, one per arm,
each with a distinct non-NULL `ref_token`, and §5's carriers match what
`encoded_ref` mints for each. That is the pre-flight promised on 2026-08-21 and
blocked by a dead postgres MCP; it now runs over `kubectl` and there is no
excuse for skipping it.
