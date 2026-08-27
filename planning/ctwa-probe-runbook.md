# Runbook — the multi-destination CTWA probe

**Date:** 2026-08-17
**Status:** **Run 2026-08-17.** Q1 answered yes; Q2 and Q3 answered for single-destination
and left open for multi. Results in §0.5; the multi ad landed on decision row **G**.
**Operator:** a human with a phone, an Ads Manager login, and `kubectl` on `vprod`.
**Cost:** zero. Nothing here activates an ad or spends money.
**Companion docs:** `planning/whatsapp-destination-model.md` (§2.1, §8 — why this
matters), `planning/click-to-whatsapp-ads.md` (the Meta reference; note its §1.3 carries
an in-place correction).

---

## 0. What this test decides

Three questions, in order of how much rides on them.

| # | Question | Why it decides something |
|---|---|---|
| **1** | Does the **Messenger** arm of a multi-destination ad still deliver the **quick-reply payload** carrying the ref? | Measured over 30 days: **68% of Messenger ad entrants (5,031 of 7,424) produce no top-level referral at all** and route *solely* through the quick-reply payload inside `page_welcome_message`. WhatsApp's autofill lives in that same blob, discriminated by the scalar `text_format.customer_action_type`. If the combined blob drops `quick_replies`, multi-destination breaks Messenger routing for two thirds of arrivals — the VIR-19 failure shape, at VIR-19 scale. |
| **2** | Does the **WhatsApp** arm prefill the autofill text, intact? | It is WhatsApp's *only* routing carrier. `url_tags` was measured in 2026-08 not to reach WhatsApp at all. |
| **3** | Does the WhatsApp arm's referral carry **`source_id`**? | Without it those arrivals have no ad id and are indistinguishable from organic entrants under the attribution design on `feature/ad-id-attribution`. |

### Already settled — do not re-test

- **Meta accepts the combined blob at creation.** `probe.multi.two` exists (ad
  `120254876245580150`, campaign `120254876244710150`), built with `--variant multi`.
- **Meta *stores* the combined blob.** Read back on 2026-08-17: `page_welcome_message`
  on that creative still contains **both** `text_format.message.autofill_message` and
  `text_format.message.quick_replies`, and `url_tags` survived on a multi-destination
  creative. `customer_action_type` did **not** act as a destructive discriminator at
  write time.
- **The open question is therefore delivery, not API acceptance.** Everything below is
  about what a phone renders and what a webhook carries.
- **Preview clicks produce genuine referrals** — no activation, no ad review, no spend
  (measured 2026-08-16).
- **`source_id` equals the ad id** on a *single-destination* CTWA referral (measured).
  Question 3 asks whether that still holds on a multi-destination ad.

---

## 0.5 Results — run of 2026-08-17

Three ads created `PAUSED` on `act_1342820622846299`, all with `--shortcode flysmoke`, all
tokens pattern-safe per §1.1:

| Variant | Creative name | Ad id | Campaign id |
|---|---|---|---|
| Messenger control | `probeMsgrAug17` | `120254903484050150` | `120254903483190150` |
| WhatsApp control | `probeWaAug17` | `120254903509150150` | `120254903508240150` |
| **Multi (under test)** | `probeMultiAug17` | `120254903561240150` | `120254903559980150` |

### Read-back, before any click (§3.3)

Run under the **corrected** `--read-back` logic (§7; the original reported false negatives
and printed its conclusion unconditionally). **[measured]**

| Ad | `autofill_message` | `quick_replies` | `url_tags` | `asset_feed_spec.additional_data` |
|---|---|---|---|---|
| Messenger control | absent | **present** | `ref=creative.probeMsgrAug17.form.flysmoke` | absent |
| WhatsApp control | **present** | absent | `None` | absent |
| Multi | **present** | **present** | `ref=creative.probeMultiAug17.form.flysmoke` | **present, both sub-structures** |
| `probe.multi.two` (`120254876245580150`) | **present** | **present** | `ref=probe.multi.two` | absent |

Each control carries exactly the one sub-structure its channel needs, and the WhatsApp
control carries no `url_tags` — matching `create_creative`'s WhatsApp branch, which drops it.
The multi creative carries all three carriers, at **both** welcome-message locations, which
the 2026-08-16 probe ad did not (§3.3's placement caveat is therefore excluded as an
explanation for anything observed here).

The re-read of `probe.multi.two` under corrected logic **confirms** §8's earlier
storage finding rather than overturning it: the combined blob does survive creation.

### Q1 — does the multi ad's Messenger arm still deliver the quick-reply payload? **Yes.** **[measured]**

The decisive result of the run. Multi ad entry at 2026-08-17 20:12:51 UTC, PSID
`1989430067808669`, after a `form.reset` at 20:12:07:

```json
"message": {
  "text": "Start survey",
  "quick_reply": {"payload": "{\"referral\": {\"ref\": \"creative.probeMultiAug17.form.flysmoke\"}}"}
}
```

Resulting state: `forms: ["flysmoke"]`, `question: "favorite_color"`, and

```json
"md": {"creative":"probeMultiAug17","form":"flysmoke","startTime":1786997570480,
       "pageid":"1855355231229529","platform":"messenger","seed":3684604491}
```

The creative's `text_format.customer_action_type` is the scalar `"autofill_message"`, and
the same blob also carries the WhatsApp `autofill_message` sub-structure — **yet Messenger
read its own sub-structure and ignored the sibling.** The feared outcome (row **B**) did not
occur: `customer_action_type` is not a destructive discriminator at delivery any more than
it is at write time.

This is the finding the whole run existed for. §2.1 of `whatsapp-destination-model.md`
measured that **68% of Messenger ad entrants route solely through this carrier**; had the
combined blob suppressed it, multi-destination would have reproduced VIR-19 at VIR-19 scale
and `type: "multi"` would never have been buildable.

The Messenger **control** behaved identically (entry 19:27:24, after a `form.reset` at
19:25:00; payload `creative.probeMsgrAug17.form.flysmoke`; `md.creative = probeMsgrAug17`;
state `RESPONDING`), which excludes rows **F** and **H** — the returning-thread confound of
§1.3 did not fire, because §3.4's reset cleared `state.forms` on both platforms.

### Q2 and Q3 — answered for single-destination, **not** for multi. **[measured / not reached]**

The WhatsApp control's arrival at 19:34:05, `userid` `15419799714`:

```json
"referral": {
  "source_id":   "120254903509150150",
  "source_type": "ad",
  "source_url":  "https://fb.me/4KwQC0Tmi",
  "ctwa_clid":   "AfjPsiJxdOxWNuItlnzwr1WkX8hON0dV7167yCHG787z…",
  "welcome_message": {"text": "Welcome! Tap below to start the survey."}
},
"text": {"body": "form.flysmoke.creative.probeWaAug17"}
```

Three things land at once:

- **`source_id` is exactly the ad id created.** Q3 resolves yes for single-destination.
- **`source_type` is literally `"ad"`**, confirming the gate value fly's B1 uses. An
  over-permissive gate would write post ids into the ad-id field, where they never match a
  mapping row and accumulate in the "unmapped" bucket that exists to catch real bugs.
- **`text.body` is the autofill, verbatim**, form-first grammar intact. Q2 resolves yes for
  single-destination, and A8's `whatsapp_autofill` serialiser is validated against real
  delivery rather than against the regex alone.

Note **no `ref` field anywhere in the referral** — the premise of the whole WhatsApp design,
now observed twice rather than once. Meta classified the conversation
`origin.type: "referral_conversion"`, `pricing.category: "referral_conversion"`,
`type: "free_entry_point"`, `billable: false`.

**The multi ad's WhatsApp arm was never reached.** The preview followed the single-valued
`object_story_spec.link_data.call_to_action` (`MESSAGE_PAGE`) to Messenger. The tester's
account is a heavy Messenger responder and Meta selects the arm by predicted
responsiveness, so this is *consistent with* the preview ignoring the `asset_feed_spec`
array — but one attempt is not proof of either. **[inferred]**

### Decision-table outcome

**The multi ad landed on row G**, with the Messenger half of rows **C**/**D**/**E**
satisfied. Rows **A**, **B**, **F** and **H** are excluded by measurement. Rows **C**, **D**
and **E** cannot be distinguished from each other without reaching the WhatsApp arm — they
differ only in what that arm does.

Row G's stated consequence stands: record the partial result, and treat activating a real
multi ad (spend + ad review) as a separate decision.

### Two confounds discovered during the run, not anticipated by §1

**No top-level referral fired on either Messenger arrival, so no `ad_id` was observable.**
Both the control and the multi ad arrived solely via `message.quick_reply.payload`, whose
contents are whatever vlab put there — `{"referral": {"ref": …}}` and nothing else. A
production Messenger *ad* referral carries `{"source":"ADS","type":"OPEN_THREAD","ref":…,
"ad_id":…}` (§2.1 of the destination-model doc, 3,153 rows in 30 days); none fired here.

Be careful what this is evidence of. It is **consistent with the measured 68% majority
pattern** — most real ad entrants produce no `OPEN_THREAD` referral either — so it is *not*
established that preview clicks specifically suppress it. What follows regardless is
operational: **Messenger-side attribution cannot be tested by preview**, because the field
that carries the ad id never appeared. It also means §9 item 4 (does `url_tags` populate
`referral.ref` on a multi-destination ad set?) remains open — this run could not test it.
**[measured absence; mechanism inferred]**

**Outbound delivery lagged by minutes on every arm.** Not a probe defect and not a routing
failure: `vlab-prod-message-worker` was ~444 messages behind on `vlab-prod-commands`, with a
single consumer against a six-partition topic, while grinding retries against an unrelated
study's bulk send. Diagnosed and written up separately in fly's
`planning/message-worker-command-lag.md`.

**This matters for anyone re-running the procedure:** an absent or slow reply is not a
result. The inbound referral lands in `chatroach.messages` immediately, independently of the
outbound worker (§1.4's point, for a different reason). Read the database; do not wait on
the phone.

---

## 1. Confounds this run is designed to exclude

Read this section. Every item here is a way to get a **confidently wrong answer**
rather than a missing one.

### 1.1 fly's deployed ref gate is the narrow one — use pattern-safe values only

Production replybot is **v0.0.218** (`devops/values/production.yaml:43`), which gates
WhatsApp entry on

```js
/^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$/i   // fly@main:event-normalizer.js:257
```

The widened pattern that also accepts `%XX` escapes exists **only on fly's unmerged
`feature/ad-id-attribution` branch** (`event-normalizer.js:289`). Meanwhile vlab's
`whatsapp_autofill` (on *vlab's* `feature/ad-id-attribution`) percent-encodes every token
through `ref_value`, which escapes `.` to `%2E` and `~` to `%7E`.

So a probe token containing a space, or a dot inside a value, would be **rejected by the
fly that is actually running**, and an empty result would be fly's version lag rather
than Meta's behaviour. You would not be able to tell those apart.

**Therefore: every token in this run stays inside `[A-Za-z0-9_-]`** — no spaces, no dots
inside values, no percent signs. Under that restriction `ref_value` is the identity
function, so the probe emits *byte-for-byte what vlab emits* while staying inside the
deployed gate. The probe now refuses to build otherwise:

```
REFUSING TO BUILD: These tokens are outside production fly's WhatsApp entry alphabet ...
```

Do not pass `--allow-unsafe-tokens` for this run.

### 1.2 The ref format the last probe shipped was not a vlab format

Production contains **exactly one** WhatsApp referral ever, from the earlier
single-destination probe:

```
text.body = "ctwaprobe.alpha.creative.Ad1H.form.probetest"
```

Parsed by fly's real code that is `{ctwaprobe: alpha, creative: Ad1H, form: probetest}`
on Messenger — but on **WhatsApp** it does not lead with `form.`, so
`WHATSAPP_ENTRY_REF` rejects it outright and the arrival fell through to
`FALLBACK_FORM` (`305`, a real researcher's survey). Verified: the state row for that
arrival reads `current_form = 305`.

The existing multi probe is no better: its token is `probe.multi.two`, which `_group`
resolves to `{probe: "multi"}` — no `form` key on either channel.

**Both existing probe ads therefore measure a format nobody will ever ship, and neither
can route.** The probe script has been changed so the tokens are *derived* from a
shortcode and a creative name by vlab's own serialisers rather than typed in by hand.
See §7 for what changed.

### 1.3 A returning Messenger thread may not render the welcome screen at all

Meta shows the welcome screen (and therefore the quick-reply button) on a **new** thread.
The tester's Messenger account already has a thread with the Virtual Lab page — PSID
`1989430067808669` walked `flysmoke`/`flysmokeb` on 2026-08-11.

If the multi ad's Messenger arm shows no button, that could mean either (a) the combined
blob dropped `quick_replies` — the finding we care about — or (b) the thread was not new.
**This is why the Messenger control ad is not optional.** Click both, back to back, from
the same device and account. The control's shape is the known-good production shape, so:

- control shows the button, multi does not → the combined blob is the cause. **Finding.**
- neither shows the button → returning-thread effect. **Not a finding.** Retry after
  deleting the thread, or from an account with no history on the page.

### 1.4 fly's no-retake rule makes an *absent* survey start meaningless

`machine.js:297-300`: if the referral's form is already anywhere in `state.forms`, the
referral is a no-op (or repeats the last question) rather than a fresh start. The tester's
Messenger PSID already has `flysmoke` in its forms array.

So **the raw referral row in `chatroach.messages` is the real measurement**, not whether
a survey visibly starts. Scribble writes `messages` straight off the Kafka topic
(`scribble/message.go:35`), independently of the machine, so the row lands regardless.

To make the end-to-end bonus observable anyway, clear the state first (§3.4).

### 1.5 `messages` dedupes on content hash

`PRIMARY KEY (hsh, userid)` where `hsh = fnv64a(content)`, inserted
`ON CONFLICT (hsh, userid) DO NOTHING` (`scribble/README.md:42`). Two byte-identical
webhooks from the same user collapse into one row. Real webhooks carry distinct
`wamid`/`mid` and timestamps so this rarely bites, but if you click twice and see one
row, that is why — do not read it as a lost referral.

### 1.6 `messages` has no timestamp index — always query by `userid`

`messages` is ~101M rows. Its only indexes are `PRIMARY KEY (hsh, userid)` and
`messages_userid_timestamp_idx (userid, timestamp)`. A `WHERE timestamp > now() - …` or a
bare `content LIKE` is a **full scan taking minutes**. Get the `userid` first (§5.1), then
query by it. That query returns instantly.

---

## 2. Preconditions

| Thing | Value | How it is obtained |
|---|---|---|
| Ad account | `act_1342820622846299` (Virtual Lab — USD) | probe default |
| Facebook Page | `1855355231229529` (Virtual Lab) | probe default `--page-id` |
| WhatsApp phone_number_id | `1203867182815254` | probe default `--phone-number-id` |
| WhatsApp dialable number | `+1-541-920-2635` | resolved at run time from `credentials` |
| Meta access token | — | read automatically from the prod `credentials` table via `kubectl exec` (`token_from_prod`). **Never** passed on argv. |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | optional | if unset you get `WARNING: token-only session`. Harmless; it only skips `appsecret_proof`. |
| Python | `adopt/.venv` | `cd adopt && poetry install` if `.venv` is missing |
| Cluster access | `kubectl` context on `vprod` | needed by the probe *and* by every SQL step |

**You need a phone.** CTWA context is mobile-only; Meta does not deliver a referral for
WhatsApp Web or Desktop (`fly/documentation/whatsapp-onboarding.md:152-153`). A desktop
click produces a false negative on questions 2 and 3.

Everything runs from:

```bash
cd /home/nandan/Documents/vlab-research/vlab/adopt
```

and all probe commands are `.venv/bin/python scripts/ctwa_probe.py …`.

---

## 3. Create the ads

Three ads. The two single-destination ones are **controls**, and §1.3 explains why the
Messenger control in particular is load-bearing rather than nice-to-have.

The shortcode is `flysmoke` for all three: a real production survey we own
(`Fly Smoke Test - Part A`, owner `nandanmarkrao@gmail.com`), so end-to-end routing
becomes observable at no extra cost. A nonexistent shortcode would route to
`FALLBACK_FORM` = `305`, someone else's live survey.

Each ad gets a distinct `--creative-name`, which is what makes the four possible tokens
distinguishable in the database. The names below are for a run on 2026-08-17; change the
suffix on a re-run so old and new arrivals cannot be confused.

### 3.1 Dry-run first — always

```bash
.venv/bin/python scripts/ctwa_probe.py \
  --variant multi \
  --creative-name probeMultiAug17 \
  --shortcode flysmoke \
  --template-ad 120254876245580150 \
  --mode dry
```

Confirm the two logged tokens read exactly:

```
messenger ref (url_tags + quick_reply.payload): creative.probeMultiAug17.form.flysmoke
whatsapp autofill (compose box):                form.flysmoke.creative.probeMultiAug17
```

Both are pattern-safe, both route to `flysmoke`, and they are **different strings** — so a
database row tells you which grammar delivered it. Verified against fly's real parsers:

| Token | Parser | Result |
|---|---|---|
| `form.flysmoke.creative.probeMultiAug17` | `WHATSAPP_ENTRY_REF` + `_group` | `{form: flysmoke, creative: probeMultiAug17}` |
| `creative.probeMultiAug17.form.flysmoke` | `_group` (Messenger) | `{creative: probeMultiAug17, form: flysmoke}` |

`--template-ad` supplies **only the image hash** — the probe writes its own headline and
body deliberately (an earlier version copied a live study's copy and promised respondents
₦1,000 of airtime for a survey that did not exist). Any ad on the account works;
`120254876245580150` is the existing multi probe. Note the borrowed *image* may still
carry a study's rendered text — acceptable because these ads are never activated and only
the tester ever sees them. Create the new ads **before** cleaning up the old ones (§8), or
pick a live ad such as `120254048243240150` as the template instead.

### 3.2 Create all three, PAUSED

```bash
# Messenger control — the known-good production shape. NOT optional (§1.3).
.venv/bin/python scripts/ctwa_probe.py \
  --variant messenger --creative-name probeMsgrAug17 \
  --shortcode flysmoke --template-ad 120254876245580150 --mode create

# WhatsApp control — single-destination CTWA, the shape vlab ships on the branch.
.venv/bin/python scripts/ctwa_probe.py \
  --variant whatsapp --creative-name probeWaAug17 \
  --shortcode flysmoke --template-ad 120254876245580150 --mode create

# The thing under test.
.venv/bin/python scripts/ctwa_probe.py \
  --variant multi --creative-name probeMultiAug17 \
  --shortcode flysmoke --template-ad 120254876245580150 --mode create
```

Each prints `campaign <id>` / `adset <id>` / `creative <id>` / `ad <id>`. **Write all
twelve ids down** — cleanup (§8) needs the campaign ids and every later step needs the ad
ids. Referral webhooks carry the **ad** id and never the campaign id.

Notes on the defaults, all of them measured rather than guessed:

- `optimization_goal` now defaults to **`LINK_CLICKS`**, not `CONVERSATIONS`. The Virtual
  Lab Page is subject to European privacy rules, which block `CONVERSATIONS` for
  click-to-WhatsApp outright (*"The goal Maximize number of conversations is not
  available for ads that click to WhatsApp because your Page is subject to privacy rules
  in Europe"*). Multi-destination accepts `LINK_CLICKS` despite Meta's guide calling
  `CONVERSATIONS` mandatory. The goal does not affect welcome-screen delivery.
- Everything is created `PAUSED`, with a `$2/day` cap that can never be charged because
  nothing is activated.
- The ad set `end_time` is midnight + 48h. If you preview after it lapses and see
  nothing, recreate rather than debug — whether an expired ad set still previews is
  **not verified**.

If an ad set create fails, the probe prints Meta's full error body and the cleanup
command. Ad set failures are the informative ones: a missing Page↔number link, a rejected
`destination_type`, or a rejected goal all surface there.

### 3.3 Read the creatives back — before clicking anything

```bash
.venv/bin/python scripts/ctwa_probe.py --read-back <MULTI_AD_ID>
```

The tail of the output states, for each of the two places a welcome message can live:

```
  autofill_message present: True
  quick_replies  present: True
```

**Both must be `True` at `object_story_spec.link_data`.** If either is `False`, Meta
dropped it at write time, the click test cannot measure delivery, and you have already
answered question 1 negatively — go to row **A** of the decision table.

The probe now also writes the blob to `asset_feed_spec.additional_data.page_welcome_message`
on the multi variant, because that is what adopt's `_create_creative` does whenever the
creative carries an `asset_feed_spec`. The first multi probe omitted it; a blank welcome
screen there would have had a mundane placement explanation and would have been misread
as "Meta dropped the combined blob".

Run `--read-back` on the two controls as well and keep the output.

### 3.4 Clear your own state, so end-to-end is observable too

Optional, and only affects the bonus (§0 question set is answered by raw referrals alone).
`REPLYBOT_RESET_SHORTCODE` is `reset` in production, and a `RESET` rebuilds from
`_initialState()` — `{state: 'START', qa: [], forms: []}` — so the no-retake rule of §1.4
stops applying.

- **WhatsApp:** send the literal text `form.reset` to **+1-541-920-2635**.
- **Messenger:** open `m.me/1855355231229529?ref=form.reset`.

Do this from the same phone and accounts you will use for the probe clicks.

> **Do not walk `flysmoke` to the end.** It is a 38-field gauntlet that exercises
> payments (Reloadly), media, and webviews. You only need the *first* message to know
> which survey started. Stop there.

---

## 4. What to click, and what to record

Get a preview link per ad:

```bash
.venv/bin/python scripts/ctwa_probe.py --preview <AD_ID>
```

Open it **on the phone**. Meta mints a fresh `preview_shareable_link` on each call; any of
them works.

Everything in this section is rendered client-side by Meta and **will not appear in any
database**. If you do not write it down as you go, it is gone. Take screenshots.

### 4.1 WhatsApp control (`probeWaAug17`) — establishes the baseline

1. Tap the ad's CTA. It should open WhatsApp on a chat with +1-541-920-2635.
2. **Before sending anything, read the compose box.** Record the text *exactly*.
   - Expected if the autofill works: `form.flysmoke.creative.probeWaAug17`
   - Expected if it does not: Meta's default, `Hello! Can I get more info on this?`
3. Record whether a greeting/welcome card appears above the compose box, and its text
   (the probe sets `Welcome! Tap below to start the survey.`).
4. Send it unmodified.
5. Record what comes back, and how long it takes.

### 4.2 Messenger control (`probeMsgrAug17`) — establishes §1.3's baseline

1. Tap the ad's CTA. It should open Messenger on a thread with the Virtual Lab page.
2. **Record whether a welcome screen with a button appears, and the button's label**
   (`Start survey`).
3. Tap the button if it is there. If it is not, send any text.
4. Record what comes back.

If **no** button appears here, you are looking at a returning thread and the Messenger
half of this run is inconclusive until you retry from a clean thread. Stop and fix that
before drawing anything from §4.3.

### 4.3 The multi ad (`probeMultiAug17`) — the actual test

This is where the procedure is least certain, and the uncertainty is worth stating in
advance rather than discovering mid-run.

**Which arm does a multi-destination ad open?** Meta's own description is that the ad
"opens a conversation … in one of the messaging apps that the person is **most likely to
respond from**" — i.e. Meta chooses, at delivery. The creative's
`object_story_spec.link_data.call_to_action` is `MESSAGE_PAGE` (Messenger) as the
single-valued fallback, and the two-element array lives in `asset_feed_spec`. **Whether an
ad *preview* honours the array, offers a choice, or always follows the fallback CTA is
not known and cannot be determined without running this.** Mark it as the first thing to
confirm.

Record, in order:

1. **What the CTA button says** on the ad unit in the preview.
2. **Which app it opens.** Messenger, WhatsApp, or a chooser.
3. If it opens **WhatsApp**: everything in §4.1, steps 2–5. The compose box is the whole
   of question 2.
4. If it opens **Messenger**: everything in §4.2, steps 2–4. The presence or absence of
   the button is the whole of question 1.
5. **Try to reach the other arm.** Reload the preview; try from a device where the other
   app is the one installed/logged in; check whether the preview offers a destination
   toggle. Record what you tried and what happened — a documented failure to reach the
   WhatsApp arm by preview is a real result, not a gap.

**If the WhatsApp arm proves unreachable by preview**, questions 2 and 3 stay open for
multi-destination specifically, and the only way through is a live activation with a tiny
budget and narrow targeting — which costs money and needs ad review. That is a decision
for the user, not something to do inside this run.

---

## 5. Read the result out of the database

The forward, from `fly/devops/port-forwards.sh` (the `postgres://` scheme is required;
`cockroachdb://` fails against libpq — `fly/documentation/secrets.md`):

```bash
kubectl -n vprod port-forward svc/gbv-cockroachdb-public 26257:26257 &
psql "postgres://root@localhost:26257/chatroach?sslmode=disable"
```

### 5.1 Identify your arrivals

Production traffic is live and concurrent, so scope everything by `userid`.

- **WhatsApp:** your own `userid` is your phone number **as digits, no `+`** — e.g.
  `15419799714`. No lookup needed.
- **Messenger:** your `userid` is the page-scoped PSID, which you cannot know in advance.
  Find it in `states`, which is ~1M rows and cheap:

```sql
-- who touched our page or our WhatsApp number recently, and where fly routed them
SELECT userid, pageid, platform, current_form, current_state, updated
  FROM states
 WHERE pageid IN ('1855355231229529', '1203867182815254')
   AND updated > now() - INTERVAL '2 hours'
 ORDER BY updated DESC;
```

`pageid` is the Facebook Page id on Messenger and the WhatsApp `phone_number_id` on
WhatsApp. `current_form = '305'` means the arrival fell through to `FALLBACK_FORM` —
i.e. the routing token did not survive. Recall §1.4: an **absent** row proves nothing.

Same query via the probe, if you would rather not port-forward:

```bash
.venv/bin/python scripts/ctwa_probe.py --find-arrivals --minutes 120
```

### 5.2 WhatsApp arm — questions 2 and 3, in one query

```sql
SELECT timestamp,
       content::jsonb -> 'referral' ->> 'source_id'    AS source_id,      -- Q3
       content::jsonb -> 'referral' ->> 'source_type'  AS source_type,
       (content::jsonb -> 'referral' ?  'ref')         AS referral_has_ref,
       content::jsonb -> 'text'     ->> 'body'         AS compose_box_text, -- Q2
       content::jsonb -> 'referral' ->> 'ctwa_clid'    AS ctwa_clid,
       content::jsonb ->> 'phone_number_id'            AS phone_number_id
  FROM messages
 WHERE userid = '<YOUR_PHONE_DIGITS>'
   AND timestamp > now() - INTERVAL '2 hours'
   AND content LIKE '%"source":"whatsapp"%'
   AND content LIKE '%"referral"%'
 ORDER BY timestamp;
```

The two `LIKE` prefilters are not decoration: at least one production `messages` row
fails `content::jsonb` outright (`invalid JSON token` inside an embedded escaped
`metadata` string), so any query casting `content` over a wide window must narrow first.

Run against the one historical CTWA arrival, this returns:

| timestamp | source_id | source_type | referral_has_ref | compose_box_text | phone_number_id |
|---|---|---|---|---|---|
| 2026-08-16 18:21:03.7+00 | 120254866237980150 | ad | f | ctwaprobe.alpha.creative.Ad1H.form.probetest | 1203867182815254 |

That is the shape to compare against. Note `referral_has_ref = f`: WhatsApp CTWA
referrals carry no `ref` field, by design — the token rides in `text.body`.

For the whole raw JSON:

```sql
SELECT timestamp, content
  FROM messages
 WHERE userid = '<YOUR_PHONE_DIGITS>'
   AND timestamp > now() - INTERVAL '2 hours'
 ORDER BY timestamp;
```

or `--capture-user <userid> --minutes 120`.

### 5.3 Messenger arm — question 1

```sql
SELECT timestamp,
       content::jsonb -> 'referral'   ->> 'source'                 AS ref_source,
       content::jsonb -> 'referral'   ->> 'type'                   AS ref_type,
       content::jsonb -> 'referral'   ->> 'ref'                    AS top_level_ref,
       content::jsonb -> 'referral'   ->> 'ad_id'                  AS ad_id,
       content::jsonb -> 'message' -> 'quick_reply' ->> 'payload'  AS quick_reply_payload
  FROM messages
 WHERE userid = '<YOUR_PSID>'
   AND timestamp > now() - INTERVAL '2 hours'
   AND content LIKE '%"source":"messenger"%'
   AND content LIKE '%referral%'
 ORDER BY timestamp;
```

Two distinct carriers, and they arrive as **separate rows**:

- **`top_level_ref`** non-null with `ref_source = ADS`, `ref_type = OPEN_THREAD` — the
  documented `messaging_referrals` webhook, populated from `AdCreative.url_tags`. This is
  the 32% carrier.
- **`quick_reply_payload`** non-null, containing `{"referral": {"ref": "…"}}` — the
  welcome-message quick reply. This is the 87% carrier, and the one at risk.

fly resolves the referral from four places in priority order — `data.referral`,
`data.postback.referral`, `postbackPayload.referral`, `quickReplyPayload.referral`
(`fly/replybot/lib/event-normalizer.js:32-35`). It does **not** read `data.message.referral`,
which Meta sometimes also sets; ignore that field.

Reference shape, from a real production ad entrant:

```
row 1  top_level_ref = creative.RC29.demo_group.Barasa Amerix.form.free2choosebase
       ad_id         = 120225449048920150   ref_source = ADS
row 2  quick_reply_payload = {"referral": {"ref": "creative.RC29.demo_group.Barasa%20Amerix.form.free2choosebase"}}
```

### 5.4 What to record from the queries

For each of the three ads, per arm actually reached:

- whether a row exists at all;
- which carrier(s) fired (`top_level_ref` / `quick_reply_payload` / `text.body`);
- the exact token string in each;
- `source_id` and `ad_id`, and whether they equal the ad id you wrote down in §3.2;
- the `current_form` on the resulting `states` row.

---

## 6. Decision table

Written **before** the run, deliberately, so the conclusion is not reasoned backwards
from whatever happens. Find the row matching the multi ad's observed behaviour.

| # | Multi ad: Messenger arm | Multi ad: WhatsApp arm | What it means | Consequence |
|---|---|---|---|---|
| **A** | `--read-back` shows `quick_replies` absent from the stored blob | — | Meta strips one sub-structure at **write** time. `customer_action_type` is a destructive discriminator after all. | The combined blob does not exist. **`type: "multi"` is not buildable.** Stop; no click test needed for Q1. |
| **B** | welcome button **absent** on screen, and **no** `quick_reply_payload` row — while the Messenger **control** shows the button and produces the row | any | Meta stores both but **delivers only the autofill**. This is the headline failure: **68% of Messenger ad entrants would land on `FALLBACK_FORM`.** | **Multi-destination cannot route to fly on both channels with the current mechanism.** Single-destination is the answer, not a stepping stone. **`type: "multi"` never gets built.** `FlyWhatsAppDestination` stays a separate sibling permanently rather than provisionally. Revisiting requires ad-id routing in fly, which is out of `ad-id-attribution.md`'s scope. |
| **C** | button present, `quick_reply_payload` carries `creative.probeMultiAug17.form.flysmoke` | compose box carries `form.flysmoke.creative.probeMultiAug17`, referral has `source_type=ad` and `source_id` = the multi ad id | **Everything works.** One blob serves both arms; both carriers survive; WhatsApp arrivals are attributable. | `FlyMultiDestination` (`whatsapp-destination-model.md` §6) is buildable as sketched — **after** §5's `destination_type` derivation lands. Q1, Q2 and Q3 all resolve yes. |
| **D** | button present and payload delivered | compose box shows Meta's **default** text (`Hello! Can I get more info on this?`) | Messenger survives; WhatsApp's only carrier is lost. Confirms `click-to-whatsapp-ads.md` §1.3's *inferred* claim, promoting it to measured. | Multi-destination routes Messenger only. Every WhatsApp arrival lands on `FALLBACK_FORM`, silently — `event-normalizer.js:295-309` emits `conversation_started` unconditionally on any `data.referral`. **Blocked behind ad-id routing in fly.** Same practical answer as row B. |
| **E** | button present and payload delivered | compose box correct, but referral has **no `source_id`** (or one that is not the ad id) | Routing works; **attribution does not**. Those arrivals cannot be joined to `ad_attributions`. | Multi-destination is usable for recruitment but its WhatsApp arm is invisible to the optimizer and to any `location: "ad"` extraction conf. Decide explicitly whether that is acceptable per study; do not let it be discovered later. |
| **F** | button **absent** — and the Messenger **control** also shows no button | any | §1.3's returning-thread effect. | **Not a finding.** Inconclusive. Retry from a Messenger account with no prior thread on page `1855355231229529`, or after deleting the thread. |
| **G** | preview only ever opens Messenger; the WhatsApp arm is unreachable | never observed | Q1 answerable, Q2/Q3 not — for multi-destination specifically. Note the **controls still answer Q2 and Q3 for single-destination**, which is what `FlyWhatsAppDestination` actually ships. | Record the partial result. Escalate the choice to activate a real multi ad (spend + ad review) as a separate decision. |
| **H** | `top_level_ref` arrives but `quick_reply_payload` does not, on **both** multi and control | — | The 32% `url_tags` carrier works; the 87% carrier did not fire *for this tester*. | Ambiguous between the returning-thread effect and a delivery change. Treat as row F: inconclusive, retry clean. |

> **Outcome, 2026-08-17: row G.** The multi ad's Messenger arm satisfied the Messenger
> half of rows **C**/**D**/**E** (button present, `quick_reply_payload` carried
> `creative.probeMultiAug17.form.flysmoke`); its WhatsApp arm was never reached, the
> preview having followed the single-valued `MESSAGE_PAGE` CTA. Rows **A**, **B**, **F**
> and **H** are excluded by measurement — see §0.5. **C**, **D** and **E** remain mutually
> indistinguishable, since they differ only in behaviour of the arm not observed.

**Rows B and D produce the same decision.** In both, multi-destination cannot route to
fly on both channels with the current mechanism, single-destination is the answer rather
than a stepping stone, and `type: "multi"` is never built. That outcome does not change
`whatsapp-destination-model.md`'s recommendation — it makes it permanent instead of
provisional. **Row B is now excluded** (§0.5), so that permanence is off the table; row D
remains live only for the unobserved WhatsApp arm.

Two findings are worth recording whatever happens, because they are cheap to observe now
and expensive to discover later:

- Whether `url_tags` populates `referral.ref` on a **multi-destination** ad set. Never
  measured there. It is the 32% floor that would still route if the button were lost.
- Whether the multi ad's WhatsApp referral's `source_id` equals the multi ad's id, which
  is `ad-id-attribution.md:656-659`'s last open question.

---

## 7. What changed in `adopt/scripts/ctwa_probe.py`

All changes are to the probe only. No application code was touched, no ads were created
or modified.

| Change | Why |
|---|---|
| Added local mirrors of `ref_value`, `shortcode_ref`, `make_ref`, `ref_metadata`, `whatsapp_autofill`, `creative_metadata` | The probe runs from `main`, where `whatsapp_autofill` does not exist. Importing would silently emit the **old** format — the `ctwaprobe.alpha.…` failure of §1.2. Copied from `../vlab-ad-id-attribution`'s `marketing.py` / `study_conf.py`, with a sync note; if the branch's serialisers change, this file is stale. |
| Routing tokens are **derived**, not typed: new `--shortcode` (default `flysmoke`), `--creative-name`, `--metadata K=V`, `--ref-mode {full,thin}` | Makes the probe emit what vlab actually produces: `make_ref` for the Messenger carriers, form-first `whatsapp_autofill` for the WhatsApp compose box. `--ref` / `--autofill` survive as explicit overrides. |
| `--ref-mode` defaults to `full` | `thin` makes both arms emit the identical string `form.flysmoke`, so a database row cannot say which grammar delivered it. `full` is also what every live Messenger study ships (`include_metadata_in_ref` defaults `True` there) and is the strictly harder case for WhatsApp — if it survives, thin survives. |
| `PATTERN_SAFE` guard: refuses to build tokens outside `[A-Za-z0-9_-]`, unless `--allow-unsafe-tokens` | §1.1. Without it a percent-encoded token silently tests fly's deployment state instead of Meta's behaviour. |
| Multi variant now also sets `asset_feed_spec.additional_data.page_welcome_message` | Mirrors `_create_creative` (branch, `marketing.py:533-541`), which sets it whenever the creative carries an `asset_feed_spec`. The first multi probe omitted it, so a blank welcome screen there would have had a placement explanation. |
| WhatsApp variant no longer emits `url_tags` | Matches `create_creative`'s WhatsApp branch, which drops it because it was measured not to reach WhatsApp. Kept on `messenger` and `multi`, where it is a live carrier. |
| `--optimization-goal` default `CONVERSATIONS` → `LINK_CLICKS` | The Virtual Lab Page is EU-privacy-restricted and rejects `CONVERSATIONS` for CTWA. The old default failed at ad set create on this Page. |
| New `--read-back AD_ID` | Prints ad, ad set and creative, decodes `page_welcome_message` at **both** locations, and states plainly whether `autofill_message` and `quick_replies` each survived. §3.3. |
| New `--preview AD_ID` | Fetches `preview_shareable_link` and prints the mobile-only warning. |
| New `--capture-user USERID --minutes N` | Index-backed replacement for `--capture`, which full-scans 101M rows and takes minutes. |
| New `--find-arrivals` | Identifies the arrival's `userid` and routed `current_form` from `states`, which is cheap to scan. §5.1. |
| Closing instructions rewritten | The old text said "activate the campaign in Ads Manager (it will spend)". Preview clicks were later measured to produce genuine referrals for free, so activation is now explicitly discouraged. |

Verified: all three variants dry-run clean; the guard rejects `--metadata "geography=north west"`;
`--read-back`, `--preview`, `--find-arrivals` and `--capture-user` all execute against
production; and both derived tokens were fed through fly's actual `WHATSAPP_ENTRY_REF` and
`_group` to confirm they resolve to `{form: flysmoke, creative: …}`.

### 7.1 Two corrections to `--read-back`, made mid-run 2026-08-17

Both are in `read_back()` (`adopt/scripts/ctwa_probe.py`), carry explanatory
comments in place, and have since been **committed** — `adopt/scripts/ctwa_probe.py` is
tracked. (This paragraph previously said they were uncommitted and that
`adopt/scripts/` was untracked; both were true when written and are not now.) They matter more than their size: `--read-back`
is §3.3's gate, and as written it could not have told you the truth about the one creative
the run depended on.

| Fix | What was wrong | Consequence if unfixed |
|---|---|---|
| **Look for `message` at the top level as well as under `text_format`** (`:540-541`) | The lookup was `(decoded.get("text_format") or {}).get("message") or {}`. The multi and WhatsApp blobs nest `message` under `text_format`; a **plain Messenger** blob puts it at the top level. So the Messenger control reported `quick_replies present: False` while the very JSON printed two lines above plainly contained the array. | A false negative on every Messenger creative. Read literally, it says the control's only routing carrier is missing — which would have made the control useless as a baseline and pointed at decision row **A** for the wrong reason. |
| **Report the conclusion conditionally** (`:549-565`) | The closing line `"Both sub-structures present => the combined blob survived creation"` was printed **unconditionally**, ignoring what the checks found. | On the multi creative — the one whose read-back decides whether the click test is even meaningful — it would have asserted the combined blob survived **whether or not Meta had stripped a sub-structure**. An operator would then have clicked on a false premise, and a negative click result would have been misattributed to *delivery* when the cause was *storage*. Rows **A** and **B** would have been indistinguishable. |

The second is the dangerous one, and it is the reason the pre-existing "the blob survives
storage" finding in `whatsapp-destination-model.md` §8 was **re-verified** under corrected
logic on ad `120254876245580150` before being relied on (§0.5). It held — but it had been
recorded from a checker that would have printed the same sentence either way.

The corrected output now distinguishes three states: both present, exactly one present
(expected for a single-destination control, fatal for a multi creative), and neither.

---

## 8. Cleanup — do this the same day

The ads are `PAUSED` and cannot spend, but a paused ad on a live ad account is one
mis-click away from recruiting real people into a smoke-test survey.

```bash
# the three campaigns created in §3.2 -- ids from the 2026-08-17 run, still live at
# the time of writing. NOT YET CLEANED UP.
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign 120254903483190150  # probeMsgrAug17
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign 120254903508240150  # probeWaAug17
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign 120254903559980150  # probeMultiAug17

# and the two from the 2026-08-16 run, whose tokens are unroutable (§1.2)
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign 120254876244710150
.venv/bin/python scripts/ctwa_probe.py --mode cleanup --campaign 120254876243850150
```

`--mode cleanup` issues `Campaign(...).api_delete()`, which removes the ad sets and ads
beneath it. Confirm nothing is left:

```bash
.venv/bin/python scripts/ctwa_probe.py --list-ads <CAMPAIGN_ID>   # expect an error or empty
```

Then stop the port-forwards:

```bash
pkill -f 'kubectl.*port-forward'
```

Leave the `flysmoke` survey alone — it is the production smoke-test survey and is used by
other runbooks.

---

## 9. Things that could not be determined without running this

Marked here so they are not mistaken for oversights. Each needs confirmation **during**
the run. Status after the 2026-08-17 run is recorded against each.

1. **Whether an ad preview of a multi-destination ad can reach the WhatsApp arm at all,
   or whether it always follows the single-valued `object_story_spec` CTA.** This is the
   single biggest risk to the run; §4.3 and decision row **G** cover it.
   → **Still open, and it is what capped the run.** Every attempt followed `MESSAGE_PAGE`
   to Messenger. Consistent with the preview ignoring `asset_feed_spec`, but the account
   used is a heavy Messenger responder and Meta assigns by predicted responsiveness, so the
   two explanations are not separated. **[inferred]**
2. **Whether the welcome screen renders for a returning Messenger thread**, and whether
   deleting the thread on the device is enough to make Meta treat it as new. §1.3, row **F**.
   → **Not tested, and no longer needed for this run.** §3.4's `form.reset` cleared
   `state.forms` on both platforms, so both Messenger arrivals started cleanly. The
   underlying Meta question is untouched.
3. **Whether a lapsed ad set (`end_time` in the past) still previews.** Recreate rather
   than investigate. → **Still open.** All three ads were previewed well inside their window.
4. **Whether `url_tags` populates `referral.ref` on a multi-destination ad set.** Measured
   on single-destination Messenger (yes) and single-destination CTWA (no). Never measured
   on multi. → **Still open.** No top-level `OPEN_THREAD` referral fired on *either*
   Messenger arrival, control or multi — so this could not be read. The absence matches the
   measured 68% majority pattern rather than being obviously preview-specific, which is
   itself why the question survives: we did not observe a negative, we observed nothing.
5. **Whether Meta's arm assignment is sticky per user**, which would make a second attempt
   from the same account land on the same arm regardless of what you do.
   → **Still open, and now load-bearing.** It decides whether reaching the WhatsApp arm
   needs a different *try* or a different *account*.

### A side finding this run did not set out to make

The reference row in §5.3 shows the **same ad**, the **same ref string**, delivered
through the two Messenger carriers with **different encodings**:

```
message.quick_reply.payload  →  creative.RC29.demo_group.Barasa%20Amerix.form.free2choosebase
referral.ref (from url_tags) →  creative.RC29.demo_group.Barasa Amerix.form.free2choosebase
```

vlab sets one string for both (`main`'s `create_creative` passes the same `ref` to
`make_welcome_message` and to `url_tags=f"ref={ref}"`). So **Meta URL-decodes `url_tags`
before surfacing it as `referral.ref`, while the quick-reply payload is delivered
verbatim.**

That is harmless today, because `main`'s `make_ref` only ever emits `%20`. It is **not**
harmless on `feature/ad-id-attribution`, where `ref_value` escapes `.` to `%2E`: if Meta
decodes `url_tags`, a metadata value containing a dot would come back as a literal `.`,
`_group` would mis-pair every token after it, and the respondent would be mis-attributed —
or, if the shifted token were `form`, mis-**routed**. The quick-reply carrier would be
correct and the `url_tags` carrier corrupt, on the same ad, for the same person.

This is one observation and should be confirmed before anything is built on it. It is
confound-free to test — Messenger's fly path is byte-identical on `main` and the branch
(`_group(pairs.map(decodeURIComponent))`), so there is no version ambiguity. The cheapest
check is to add `--metadata cluster=a.b` to the **Messenger control only**, with
`--allow-unsafe-tokens`, and compare the two carriers on arrival. It is deliberately kept
out of the main run so it cannot contaminate questions 1–3.

> **Status after 2026-08-17: still open, and now the highest-value cheap check remaining.**
> The run did not touch it — the check was deliberately excluded, every token was
> pattern-safe by construction (§1.1), and no `OPEN_THREAD` referral fired on either
> Messenger arrival, so there was no `url_tags`-derived `ref` to compare against anything.
>
> It has since become a **merge gate**, not just a curiosity. vlab's D2 work now escapes
> `.` to `%2E` and `~` to `%7E` in `make_ref` — including the creative name, which is
> interpolated unquoted and whose corruption mis-*routes* rather than mis-attributes. If
> Meta decodes `url_tags`, D2's escaping is silently undone on that carrier while working
> correctly on the quick-reply carrier: the same ad, the same person, one carrier right and
> one wrong, with no error anywhere. **D2 should not merge until this is settled.**
>
> Note the check needs a top-level referral to fire in order to produce a reading at all —
> which this run showed cannot be relied on (§9 item 4). Budget for the possibility that it
> takes several attempts, or a `SHORTLINK` entry via `m.me/…?ref=…` rather than an ad click,
> to get both carriers on the same arrival.
