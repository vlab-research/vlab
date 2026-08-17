# Multi-destination ads

**Status:** built, tested, and **gated off**. The WhatsApp arm has never been
observed. §4 is the procedure that clears the gate; until it is run and recorded,
`type: "multi"` refuses to load from a study conf.

**Scope:** one ad that opens either Messenger or WhatsApp, Meta choosing per
respondent, and the ad-set `destination_type` derivation that had to land first.

**Companion reading:**
- `planning/whatsapp-destination-model.md` — why multi is a third destination
  type rather than a `platforms` list, and what was measured on 2026-08-17
- `planning/click-to-whatsapp-ads.md` §1.2 — Meta's multi-destination format
- `adopt/README.md` — where these functions live in the code
- `documentation/ad-attributions.md` — the frozen blob this must not disturb

---

## 1. What a multi-destination ad is, and what it costs

Meta's description: the ad "opens a conversation with the business in one of the
messaging apps that the person is most likely to respond from." That is an
**optimisation objective**, and it cuts two ways.

For a study where channel is a nuisance parameter — most studies — it is a free
reduction in cost per respondent. For a study where channel is the treatment it
is fatal: **you cannot randomise what Meta assigns.** Arm selection is an
unobserved, non-random mechanism optimised on predicted responsiveness, and
channel correlates with demographics, so who lands on WhatsApp versus Messenger
is systematically non-random in a way nothing in the stored data records.

Attribution is untouched — one ad, one ad id, one stratum, one
`ad_attributions` row, and the mapping is channel-agnostic by construction. But
channel is no longer derivable from the ad id. It is recoverable only from
`md.platform` on the response record, never from the mapping table.

**If you want to compare channels, use two single-destination destinations in a
`DestinationRecruitmentExperiment`** — which is what the derivation in §2 makes
possible for the first time.

---

## 2. `destination_type` is derived at the ad set

`destination_type` is an ad-set field; destinations are named per creative. So
channel is necessarily uniform within a stratum, and something has to agree the
value across the stratum's pairs.

It used to be **one string on the recruitment conf**, consumed by every ad set of
every arm. Two consequences, both live until now:

- A study could not have a Messenger arm and a WhatsApp arm in a
  `DestinationRecruitmentExperiment`. Setting `MESSAGING_MESSENGER_WHATSAPP` made
  *both* arms multi-destination and destroyed the experiment.
- A study whose `destination_type` disagreed with its destinations built happily
  and misrouted silently.

Now: `destination_type_for(destination)` (`adopt/study_conf.py`) gives the token
one destination implies, and `adset_destination_type(pairs, recruitment_default)`
(`adopt/marketing.py`) agrees it across a stratum — shaped exactly like the
`promoted_object_for` / `adset_promoted_object` pair beside it.

| Destination | Implied `destination_type` |
|---|---|
| `FlyMessengerDestination` | `MESSENGER` |
| `FlyWhatsAppDestination` | `WHATSAPP` |
| `FlyMultiDestination` | `MESSAGING_MESSENGER_WHATSAPP` |
| `WebDestination`, `AppDestination` | *none* — the recruitment conf's value is used |

Disagreement **within one stratum** raises. Disagreement between arms is the
point and does not.

### Why this changes nothing for existing studies

Measured against production `study_confs`, 2026-08-17:

| Recruitment `destination_type` | Destination types | Studies | Result |
|---|---|---|---|
| `MESSENGER` | `messenger` | 110 | derives `MESSENGER` — identical |
| *absent* | `messenger` / null | 22 | already fails to build; `destination_type` is a required field |
| `WEBSITE` | `website` | 2 | Web implies nothing → stored value used verbatim |
| `WEB` | `web` | 1 | same |
| *absent* | `web` | 1 | same |
| `WEB` | **`messenger`** | 2 | now derives `MESSENGER` — **both ended April 2024** |

The last row is the only behaviour change, and it affects no running study.

### It cannot rewrite a live ad set

`destination_type` and `promoted_object` are **absent from
`field_contract.COMPARED_ADSET`**, so they ride only on ad-set *creates*.
`test_reconciliation.py` asserts this directly. Two consequences:

1. Landing this derivation cannot rewrite anything that already exists.
2. **A running study can never change channel.** Ad sets are matched by name and
   the name is the stratum id, so they persist for the study's lifetime. Say
   this in the UI.

### The two silent holes, now loud

`StudyConf.check_destination_type_matches_destinations` fails at config time —
before any ad exists — when the recruitment conf names a messaging
`destination_type` that none of the study's destinations provides:

- `MESSAGING_MESSENGER_WHATSAPP` + only Messenger destinations
- `MESSAGING_MESSENGER_WHATSAPP` + only WhatsApp destinations

Both used to pass. Both produce an ad where one arm routes correctly and the
other carries no routing token at all, so its respondents fall through to
`FALLBACK_FORM` — production survey `305`, a real survey belonging to a real
researcher, where misrouted people hit `END` and look like completions. Half the
ad works, which is exactly why nobody notices. That failure ran four days and
1,770 users in July 2026 (VIR-19).

A **non-messaging** `destination_type` (WEB, WEBSITE, APP) makes no claim about
which messaging app opens, so it is not checked — that is what keeps the legacy
studies above building.

---

## 3. `FlyMultiDestination`

```python
class FlyMultiDestination(BaseModel):
    type: Literal["multi"]
    name: str
    initial_shortcode: str          # ONE shortcode — see below
    welcome_message: str
    button_text: str                # the Messenger arm's quick reply
    whatsapp_phone_number: str      # the WhatsApp arm's promoted_object
    additional_metadata: Optional[dict[str, str]] = None
    include_metadata_in_ref: bool = False
```

A **third** destination type, not a `platforms` list on a merged class. The
reasoning is in `planning/whatsapp-destination-model.md`: Messenger and WhatsApp
differ in the grammar their routing token must obey, in whether the respondent
can see and edit it, in which fields are required, and in what a
misconfiguration costs.

**One shortcode, not one per channel.** `creative_metadata` folds
`form: initial_shortcode` into the frozen blob and there is exactly one blob per
ad; a per-channel shortcode would mean one ad whose two arms belong to two
surveys and one mapping row that can only name one of them.

**`include_metadata_in_ref` defaults `False`** — WhatsApp's default wins, because
the WhatsApp arm's token sits in the respondent's compose box where they can read
and edit it. One flag drives both arms, so they cannot disagree about how much
they disclose.

### Three carriers on one creative

| Carrier | Field | Serves | Share of Messenger entrants |
|---|---|---|---|
| `url_tags` | creative-level | Messenger `referral.ref` | 32% |
| `quick_replies[].payload` | inside `page_welcome_message` | Messenger | **68%, and their only carrier** |
| `autofill_message.content` | inside `page_welcome_message` | WhatsApp | its only carrier of any kind |

The last two are sub-structures of **one** `page_welcome_message` string, and
`text_format.customer_action_type` is a scalar naming only `autofill_message`.
Both are nevertheless stored and — on the Messenger side — delivered.
`make_multi_welcome_message` builds that blob, byte-identical to
`adopt/scripts/ctwa_probe.py`'s `welcome_combined`, which is the code that
actually produced the measurement. A test asserts the two stay equal.

The two tokens are **different serialisations of the same facts**, deliberately:
`make_ref` leads with `creative.` and is order-free; `whatsapp_autofill` is
form-first because fly's entry pattern anchors on `form.`, so `make_ref` output
can never match it whatever the values are. Both parse back to exactly the blob
frozen into `ad_attributions.metadata`.

### The rest of the shape

- `object_story_spec.link_data.call_to_action` stays **single-valued**
  (`MESSAGE_PAGE`) as Meta's documented fallback.
- `asset_feed_spec` carries the real array under
  `optimization_type: "DOF_MESSAGING_DESTINATION"`. There is no `messaging_apps`
  field and no list-valued destination field — the combination is a single enum
  token, and the creative's destinations must match the ad set's.
- A template that **already carries an `asset_feed_spec` raises**.
  `asset_feed_spec` holds one `optimization_type`; merging would silently drop
  either the destination array or the template's creative variants, and neither
  is inferable from the config.

### Constraints that couple to study-level settings

- **`optimization_goal` must be `CONVERSATIONS`.** Validated at config time,
  naming both fields; not silently overridden, because `optimization_goal` is
  what cost-per-respondent is measured against.
- `billing_event` must be `IMPRESSIONS` — already unconditional.
- `special_ad_categories` must be empty — already hardcoded `[]`.

> ⚠️ **A conflict you may hit immediately.** The Virtual Lab Page is subject to
> European privacy rules, which block `CONVERSATIONS` for click-to-WhatsApp
> outright (*"The goal Maximize number of conversations is not available…"*,
> subcode 3858658). Separately, this repo has measured
> `MESSAGING_MESSENGER_WHATSAPP` + `LINK_CLICKS` being **accepted** on a live ad
> set, contradicting Meta's own guide. So on such a Page the two constraints
> genuinely conflict and no multi ad is configurable. That is a real finding
> about the Page, surfaced at config time rather than mid-run. If it blocks a
> study that needs multi, the decision to relax the `CONVERSATIONS` check should
> be made deliberately and recorded here — not worked around in a conf.

---

## 4. The gate, and the measurement that clears it

### 4.1 What is measured, and what is not

**Measured (2026-08-17, real Meta delivery, ad `120254903561240150`):** the
Messenger arm of a multi ad delivers its quick-reply payload with the ref intact
— `{"referral": {"ref": "creative.probeMultiAug17.form.flysmoke"}}` — even though
`customer_action_type` is the scalar `"autofill_message"`. **Messenger reads its
own sub-structure and ignores the sibling.** Meta also stores both halves without
stripping either, confirmed by reading the creative back. This was the outcome
that would have killed multi-destination. It did not happen.

**Not measured: the WhatsApp arm of a multi ad.** The preview followed the
single-valued `MESSAGE_PAGE` CTA to Messenger on every attempt. We *expect*
symmetry — the Messenger arm ignored its sibling, so the WhatsApp arm should too
— but **nobody has seen it.**

If that inference is wrong, Meta serves its own default prefill ("Hello! Can I
get more info on this?"), fly's `event-normalizer.js` emits
`conversation_started` **unconditionally** on any `data.referral`, and every
WhatsApp respondent lands silently on `FALLBACK_FORM`. They look like
completions. That is VIR-19 again, on a feature nobody is watching yet.

**Hence the gate.** `FlyMultiDestination` refuses to construct unless
`ADOPT_ENABLE_MULTI_DESTINATION` is truthy. The type is built, tested and
reviewable; it cannot be configured by accident.

### 4.2 Procedure A — steer the preview to the WhatsApp arm (cheapest, do this first)

The blocker is that a preview click follows the single-valued
`object_story_spec.link_data.call_to_action`. `--multi-fallback whatsapp` points
that CTA at WhatsApp while leaving **the ad set, the combined welcome blob and
the `asset_feed_spec` destination array byte-identical** (asserted in the
verification snippet in §4.4). That isolates the question that actually matters.

```bash
cd adopt

# 1. Build the probe ad. PAUSED; nothing delivers, nothing spends.
python scripts/ctwa_probe.py --variant multi --mode create \
    --multi-fallback whatsapp \
    --shortcode flysmoke \
    --creative-name probeMultiWaArm \
    --template-ad <AN_EXISTING_AD_ID>

# 2. Confirm Meta STORED both sub-structures before clicking anything.
#    If the blob lost its quick_replies here, the click is measuring a
#    creative that never carried the thing under test.
python scripts/ctwa_probe.py --read-back <AD_ID>

# 3. Get the preview link and open it ON A PHONE. CTWA context is
#    mobile-only; Meta does not deliver a referral for WhatsApp Web/Desktop,
#    so a desktop click produces a false negative.
python scripts/ctwa_probe.py --preview <AD_ID>

# 4. BEFORE SENDING, read the compose box and write down what it says.
#    This is the measurement. Then send it.

# 5. Find the arrival and read the raw webhook.
python scripts/ctwa_probe.py --find-arrivals --minutes 30
python scripts/ctwa_probe.py --capture-user <USERID> --minutes 30

# 6. Clean up.
python scripts/ctwa_probe.py --mode cleanup --campaign <CAMPAIGN_ID>
```

**Four things to record**, and all four go in §4.5:

| # | What | Pass |
|---|---|---|
| a | is there a `referral` object at all | yes |
| b | `referral.source_type` | exactly `"ad"` |
| c | `referral.source_id` | exactly the multi ad's id |
| d | **`text.body`** | `form.flysmoke`, verbatim — **not** Meta's default prefill |

**(d) is the one that decides it.** If the compose box holds Meta's default
text, multi-destination cannot route to fly on WhatsApp with the current
mechanism, and the feature stays gated until an ad-id routing path exists in fly
— which does not exist and is out of scope for the attribution design.

Also confirm `current_form` in `states` is **not** `305`. `305` is
`FALLBACK_FORM`: the routing token did not survive.

> **The caveat, and it is not optional.** Procedure A measures *the blob*: it
> shows whether the WhatsApp side reads its own sub-structure out of a
> `page_welcome_message` that also carries `quick_replies`, on a
> `MESSAGING_MESSENGER_WHATSAPP` ad set. It does **not** exercise Meta's organic
> arm-selection path, because we chose the arm rather than letting Meta choose.
> A pass is strong evidence — it removes the only mechanism by which the
> WhatsApp arm could plausibly lose its token — but it is not the same thing as
> observing an organically-assigned WhatsApp arrival. Record it as what it is.

### 4.3 Procedure B — an organically assigned arm (confirmatory)

Meta assigns the arm by predicted responsiveness, and the usual tester is a heavy
Messenger responder, which is the likeliest reason every preview went to
Messenger. In ascending cost:

1. **Disable or log out of Messenger on the test device**, then preview a normal
   `--multi-fallback messenger` build.
2. **Use a second Facebook account with no Messenger history** on page
   `1855355231229529`. Note the open question of whether Meta's assignment is
   *sticky per user* — if it is, retrying from the same account proves nothing
   and a different account is required rather than a different attempt.
3. **Activate a real multi ad** with a tiny budget and narrow targeting. Costs
   money and needs ad review. This is the only procedure that observes the real
   thing end to end.

### 4.4 Verifying the probe still measures what we ship

The probe keeps its own copy of the serialisers deliberately. Before trusting a
run, confirm the copy has not gone stale:

```bash
cd adopt && python - <<'EOF'
import importlib.util
spec = importlib.util.spec_from_file_location("p", "scripts/ctwa_probe.py")
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
from adopt.marketing import make_multi_welcome_message

assert p.welcome_combined("g", "b", "r", "a") == make_multi_welcome_message("g", "b", "r", "a")

a = p.build_creative("multi", {}, "p", "r", "g", "b", "a", "h", "t", "n", "messenger")
b = p.build_creative("multi", {}, "p", "r", "g", "b", "a", "h", "t", "n", "whatsapp")
assert a["asset_feed_spec"] == b["asset_feed_spec"]
assert (a["object_story_spec"]["link_data"]["page_welcome_message"]
        == b["object_story_spec"]["link_data"]["page_welcome_message"])
print("probe agrees with marketing.py, and the fallback changes only the CTA")
EOF
```

`test_marketing.py::test_the_multi_welcome_blob_is_byte_identical_to_the_probes`
holds the first of these in CI.

### 4.5 Result log

**Nothing here yet. The gate stays shut until there is.**

Record each attempt, including failures and inconclusive runs — an inconclusive
run is why this section exists.

| Date | Procedure | Ad id | Compose box held | `source_type` / `source_id` | `current_form` | Verdict |
|---|---|---|---|---|---|---|
| | | | | | | |

Once a run passes on (a)–(d), set `ADOPT_ENABLE_MULTI_DESTINATION=true` in the
deployment's env (via `devops/values/<env>.yaml`, per the
infrastructure-as-code rule — never `kubectl set env`), and note here which
environments are enabled.

---

## 5. What is deliberately not built

- **The dashboard form.** `grep -rn multi dashboard/src/` returns nothing.
  `FlyMultiDestination` is reachable only by hand-POSTing a conf, which is
  appropriate while gated. Blocked on other concurrent work in
  `dashboard/src/pages/StudyConfPage/forms/destinations/`.
- **Instagram.** `MESSAGING_INSTAGRAM_DIRECT_*` tokens exist and nothing is known
  about what an Instagram Direct arrival carries — whether there is a ref carrier
  at all, or an equivalent of `source_id`. fly has no Instagram normalizer,
  receiver or send path either. The destination-type vocabulary accommodates
  these tokens; nothing else does.
- **Changing channel on a running study.** Structurally impossible; see §2.
