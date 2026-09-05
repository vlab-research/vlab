# Template authoring: campaigns, ad sets and creatives from the SDK

Implemented 2026-09-05 on `feature/template-authoring`. This is the phase-notes
file for the last bullet of `planning/agent-study-authoring.md` §10 — "creating
template campaigns, ad sets and ads ... the SDK uses the Facebook Business SDK
directly, later; no write proxy" — written in the discipline of that document's
§11–§14 and of `planning/vlab-sdk.md`: what shipped, the decisions with their
reasons, what the plan and the prior art got wrong, and what is deliberately
not done or still open.

The decision **not** to build a `meta:write` proxy is settled and is not
relitigated here. §10's reasoning still holds: a write proxy makes the conf
service an image-upload relay (bytes in, bytes to Meta, size limits, the
event-loop discipline of §13.4) on top of taking on money-spending liability
that needs paused-only and budget-ceiling guardrails plus an audit trail.
`meta:write` stays defined and unserved.

---

## 1. What shipped

| | |
|---|---|
| `adopt/adopt/authoring/templates.py` | The library. A pure planner (`plan_template_campaign`, `plan_template_ads`), a creative builder (`build_creative`) for all five destination kinds, `apply`, `delete_template_campaign`, `find_campaign_by_name`, `validate_targeting`. |
| `adopt/adopt/sdk/templates_cli.py` | `vlab template plan\|create\|creative\|delete\|check-targeting`. All `--json`. Dry run by default. |
| `adopt/adopt/meta_fields.py` | The Graph `fields` lists, extracted from `server/meta.py` so the builder and the proxy name the same fields. |
| `adopt/adopt/facebook/state.py` | `api_for_token` — the one place a `FacebookSession` is constructed. `get_api` delegates to it. |
| `adopt/adopt/sdk/cli.py` | **One line**: `from . import templates_cli` at the bottom. |
| tests | `authoring/test_templates.py` (74), `sdk/test_templates_cli.py` (27). No database, no live Meta; the mock boundary is `FacebookAdsApi.call`, as in `server/test_meta.py`. |
| docs | `documentation/agent-api.md` §6a (new, and the single home for the Meta quirks §10 asked to have promoted), §3 `creatives` pointer, §7 item 2 corrected, §8 entry. `adopt/README.md` gains a `vlab template` section. |

DB-free suite 1 564 → 1 665 passed locally (Docker is down on the author's
machine, so the ~100 database-backed tests were not run here); the full suite
runs in CI.

`adopt/scripts/make_template_campaign.py` is **superseded** by this library and
should be deleted once someone has run `vlab template create` against live Meta
once. It is untracked, so nothing here removes it; §5 records what it got wrong.

---

## 2. The decision the module rests on: plan is pure, and a dry run IS the plan

`plan_template_campaign` has no sockets, no clock and no randomness. It returns
the exact Graph calls — method, edge, parameters — as JSON, with `${ref}`
placeholders for ids that do not exist yet, and `apply` substitutes them as it
goes.

Three things follow, and they are the reason it is shaped this way rather than
as a `create_template_campaign(...)` that does the obvious thing:

1. **`vlab template plan` needs no Facebook token at all**, so it runs in
   review, in CI, and on a machine that has no business holding one. There is a
   test that asserts it never touches the network.
2. **A plan is diffable and committable.** The golden test in
   `test_templates.py` is the whole plan as a literal, on purpose: this is what
   gets created on somebody's ad account, and a diff there should be looked at
   even when every other test still passes.
3. **Every check that does not need Meta happens before anything exists.** The
   declared-property contract, the budget ceiling, unknown spec keys, a missing
   image file, a WhatsApp ad set with no Page. The alternative is discovering
   them four objects into an apply, with the first three left behind and no
   rollback.

The placeholder is whole-string only (`"${vlab:campaign}"` is a value, never a
fragment inside a sentence), so there is no partial interpolation to get wrong
and no way for a Meta-supplied string to be treated as a template. The one
asymmetry worth remembering: a placeholder resolves to an **id** for a
campaign, ad set or creative, and to the **image hash** for an upload — because
a hash is what a creative references.

**The `vlab:` namespace was added in self-review, and it earns its ugliness.**
`_substitute` walks every string in a create's params, and those params include
the researcher's own ad copy. Under the original bare `${...}` syntax, a
message reading exactly `"${discount}"` was either substituted or — because an
unknown ref is deliberately a hard error, being a planner bug — failed the
whole apply on an ad that was fine. Namespacing means a collision needs a
message that is exactly `${vlab:<a ref this plan defines>}`, which lets the
unknown-ref guard stay a hard error rather than degrading to "leave it alone",
which would have hidden real bugs. Two tests pin both halves.

Ordering is images → campaign → ad sets → creatives → ads. Uploads lead because
an image is cheap, reusable and orphan-safe, while a campaign left behind by a
failed upload is debris on someone's account.

---

## 3. The creative builder, which is the whole point

Targeting can be lifted off any ad set that already exists. A creative cannot:
it needs an uploaded image, a Page, copy, and a call-to-action that agrees with
the destination — and that is the thing a researcher was previously stuck doing
by hand in Ads Manager.

`build_creative(kind, ...)` produces the `POST /act_<id>/adcreatives` body for
each of the five kinds vlab supports: `messenger`, `whatsapp`, `multi`, `web`,
`app`. What it produces is defined by what `marketing._create_creative` reads
back off it, which is the contract documented in `agent-api.md` §6a: some
fields are copied verbatim (the researcher's half — image, copy, Page,
Instagram account) and the destination-bearing ones are overridden per
destination (the study conf's half — CTA, link, `page_welcome_message`,
`url_tags`).

**The CTAs and links are imported from `marketing`, not restated.** A template
whose CTA disagreed with what the runtime builds would be a template that looks
right in Ads Manager and ships something else. `messenger_call_to_action`,
`whatsapp_call_to_action`, `web_call_to_action`,
`app_download_call_to_action`, `multi_destination_asset_feed_spec`,
`MESSENGER_LINK_FALLBACK` and `WHATSAPP_LINK` all come from there. This is §7's
"one implementation" applied to the one place it would have been easy to skip.

### The one addition: a single-destination `asset_feed_spec`

`build_creative` emits a one-entry `DOF_MESSAGING_DESTINATION` spec on
messenger and whatsapp creatives (and Meta's documented two-entry one on
multi). That is not an invention — `refuse_template_destination_conflicts`'
own comment says "a template built in Ads Manager AS a click-to-messaging ad
already carries a DOF_MESSAGING_DESTINATION spec", and the check had to be
narrowed in 2026-08 precisely because it was refusing those ordinary templates.

It is there because **it is what makes a template say what it is for.** Without
it, a Messenger template and a WhatsApp template are indistinguishable to
`refuse_template_destination_conflicts` (`have` is empty, so it returns early),
and pointing a creative at the wrong one is caught by nothing. It is not
silently *wrong* — the runtime overrides the CTA and the link, so the ad that
ships is correct for the destination the conf names — but it is not the ad the
researcher was looking at, and the whole reason
`planning/creative-construction-contract.md` refuses rather than overwrites is
that quietly shipping a different ad is the failure mode this codebase fights
everywhere else.

`declare_destination=False` turns it off, for a caller who wants a template
that says nothing.

---

## 4. Decisions worth their own line

**The marker is a name prefix, `Templates - `, not an ad label.** Both were on
the table. An ad label is a separate Graph object that has to be created,
referenced by id on every child and read back with an extra field expansion —
three more failure modes — and it is invisible in the one place a human looks,
the campaign list in Ads Manager. The prefix is visible there, it is already
the convention on the production account (`Templates - VapeFree`,
`Templates - Shujaaz - Free2Choose`), and it survives `GET /{org}/meta/campaigns`,
whose `fields` is `name,id` and carries no labels. The cost is that a human can
rename a campaign into or out of the marker; that is accepted, and
`delete_template_campaign` says so when it refuses.

**`create` refuses a taken campaign name rather than reusing it.** Lifted from
the script, and the reason is stronger than "it would confuse a human": two
campaigns with one name make `FacebookState.campaign` raise `StateNameError`,
so a duplicate breaks the run path of any study naming that campaign. Delete
and re-run is the recoverable path.

**`delete` refuses a marked campaign that is delivering.** Belt and braces on
top of the marker. A template is created PAUSED and should never be delivering;
if it is, somebody activated it and the reason is not knowable from a CLI.
`--force` skips only that second check — nothing skips the marker.

**The created creative is read back, not echoed.** What a study stores as
`creatives[].template` is what the Meta proxy returns, which is not what was
sent: Meta fills in `actor_id`, rewrites `object_story_spec`, and drops fields
it did not accept. Handing the caller the sent params as if they were the
template would produce a `creatives` conf that has never existed on Meta — and
`actor_id`, which `audiences.py:150` reads with a bare `KeyError`, is exactly
one of the fields Meta derives rather than echoes. `apply` checks the read-back
against `meta_fields.REQUIRED_TEMPLATE_CREATIVE_FIELDS` and warns rather than
assuming.

**Raw `api.call`, not the SDK's typed `AdAccount.create_*` helpers.** Those
validate parameter names against a hardcoded `param_types` map, and
`is_adset_budget_sharing_enabled` — the campaign field whose absence is a 400
with subcode 4834011 — is not in `create_campaign`'s map in facebook-business
v22. Raw `call` also puts the mock boundary in exactly one place, which is
where `server/test_meta.py` puts it.

**`adopt.facebook.api.call` is deliberately not reused**, for the same reason
the Meta proxy does not reuse it (§13.4): it retries codes 2/17/368/80004
forever at five-minute intervals with no attempt cap. That is right for a cron
with hours to spend and wrong for a CLI a human is watching — and worse than
wrong for a *create*, where a retried POST that actually succeeded the first
time leaves a duplicate object on the account.

**Objective / optimization_goal / destination_type pairings are WARNED about,
not refused.** Meta pairs the three, and its own documentation contradicts
itself about which triples are legal — the `destination_type` guide's objective
table omits WHATSAPP for OUTCOME_LEADS and OUTCOME_SALES while the
click-to-WhatsApp page lists both (`planning/click-to-whatsapp-ads.md` §1.1) —
and the allowed set moves between Graph versions. A hardcoded matrix in the
planner would go wrong silently and would then refuse plans Meta would have
accepted, which is worse than saying "check this". So the planner warns on the
pairings that actually bite: a web or app ad set left on the click-to-messaging
defaults, a multi ad set off CONVERSATIONS, an app ad set with no
`promoted_object.application_id`. Contrast the budget ceiling and the
declared-property check, which are refusals because both are facts about this
repository rather than about Meta's current enum tables.

**A YAML spec for `plan`/`create`, flags for everything else.** A campaign has
many ad sets and many ads, and neither is expressible in flags without
inventing a mini-language; the spec is also the artifact worth committing next
to the study. `creative`, `delete` and `check-targeting` are single-object
commands and take flags. The spec has **no schema of its own** — its keys are
the `AdsetSpec` / `AdSpec` field names — for the reason `vlab-sdk.md` §5 gives
about `study.yaml`: the moment the file has a schema, the library owns a second
definition of what a template is.

**An unknown spec key is an error, not a drop.** `vlab-sdk.md` §4 argues this
for conf models; here the cost is higher, because by the time you notice, the
object is on someone's ad account.

**Image paths resolve relative to the SPEC, not the shell's cwd.** A spec
committed next to its images has to work from anywhere.

**`marketing` is imported lazily, inside the three functions that need it.**
Measured: `adopt.marketing` costs 1.4 s to import, because `adopt.budget` pulls
cvxpy. `adopt.sdk.cli` registers the `vlab template` group at import time, so a
module-level import would have put that 1.4 s in front of **every** `vlab`
command — `vlab validate` included, whose entire selling point is being instant
and offline. Nothing is copied; only *when* `marketing` is read changes.
`adopt.sdk.cli` imports in 0.76 s, essentially unchanged.

**`cli.py`'s share of the feature is one line.** `from . import templates_cli`
at the bottom; the module hangs itself off `cli` with its own `@cli.group`.
Both import orders work — the import binds a module object rather than reaching
for an attribute of a half-initialised module — and there is a test that
reloads them in the other order. This was a brief constraint (keep the merge
with PR #265's review fixes trivial) that turned out to be the better design
anyway: the group's error handling, its options and its help all live with the
group.

---

## 5. What the prior art got wrong

`adopt/scripts/make_template_campaign.py` is the best existing knowledge about
templates and almost all of it is right. Two things are not.

**1. `targeting_automation` does not need to be declared, and declaring it is
harmful.** The script's docstring says it "has to be set and has to be
declared", with a correct explanation of why setting it matters (Meta's
Advantage audience expansion is ON by default and leaks delivery outside the
stratum being measured). The declaring half is no longer true and is now
actively bad:

* `extract_from_adset` **forces** `targeting_automation = {"advantage_audience": 0}`
  onto every extraction, regardless of what was declared or what the source ad
  set held — its own comment calls this "a deliberate policy decision, not a
  fallback". So the study's ad sets get it either way.
* `diff_property_keys` strips `targeting_automation` from the **stored** key
  set and not from the **current** property list — plan §12.3 item 4, a
  TypeScript bug ported faithfully. A variable that declares it therefore shows
  the dashboard's two-line "properties drifted" banner forever, with nothing a
  researcher can do about it.

So `DEFAULT_PROPERTIES` is `genders, age_min, age_max, geo_locations`;
`targeting_automation` is set on every planned ad set anyway (a template is
read by humans too, and an ad set that says it does not use Advantage audience
is the honest artifact), and declaring it is a plan **warning** that says
exactly this. `planning/encoded-ref-probe-runbook.md` §3.5 repeats the script's
advice and is wrong in the same way; it is left alone as a historical record of
what was done on that probe.

**2. The script creates no ads, and says so as if it were a limitation of
scope.** It is the limitation that mattered: "add your creative to this
campaign in Ads Manager before picking it there" is precisely the step an agent
cannot take, and it is why this library exists.

Everything else the script knew is preserved verbatim, with its measurement
date: `is_adset_budget_sharing_enabled: false` or 400/4834011; the unremovable
`frequently_in`; region-name canonicalisation; PAUSED everywhere; the duplicate
name refusal and *why* it matters; the Kwara region key, hardcoded rather than
searched so a rerun cannot silently pick a different region.

**What §10 of the plan got right, and one thing it did not say.** §10 predicted
"two things — get a Meta-validated targeting dict ... and build a creative,
which is an unavoidable Meta write because it needs an uploaded image or video
hash". Both correct. What it did not anticipate is that the *third* thing —
the ad — is where the join lives: the Creatives form reads ads, not creatives,
so a campaign full of creatives with no ads configures nothing. The ad also
carries the name that `mint_ref_token` is keyed on.

---


## 5a. What a pre-merge review found

A read-through of the branch (2026-09-05, before the PR), with the plan and
apply paths exercised for every creative kind. It found no way to create an
ACTIVE object and no way to bypass either refusal from the CLI, and confirmed
that `server/test_meta.py`'s four literal `fields` assertions still hold byte
for byte after the `meta_fields.py` extraction (they could not be run locally:
Docker is down, and that module's tests need a database). What it did find, all
fixed on the branch:

1. **A web *video* creative with no link planned cleanly and shipped
   `call_to_action.value.link = null`.** The "a web creative needs a link"
   guard lived in `_structural_link`, which only the `link_data` (image) branch
   calls; the `video_data` branch went straight to `_call_to_action_for`. Meta
   rejects that at `POST /adcreatives` — after the campaign and its ad sets
   exist — which is the exact failure plan-time checks are for. The
   requirement is now in `build_creative`'s validation block, beside the
   app/deeplink one.
2. **`_fill_promoted_object` treated an ad with no `adset` as belonging to
   every ad set.** Such an ad actually hangs on the *first* one, so a WhatsApp
   ad set with no ads of its own silently inherited a Page from an ad hanging
   somewhere else — and the function's own "no ad in this plan hangs on it"
   message was unreachable in precisely the case it describes. The default is
   now resolved before filtering, from the same value `_plan_ads` uses.
3. **`apply`'s two refusals were an `if/elif` with no `else`.** A plan naming
   neither a campaign to create nor one to add to skipped both checks and
   created objects. Not reachable from either constructor today, which is why
   it is now a raise rather than a comment: this is the only place the
   refusals live, and a future third constructor should have to notice.
4. **`check-targeting --spec` skipped the unknown-key check `plan` applies.**
   A spec with a misspelled ad-set key exited 0 here and 1 under `plan` — and
   check-targeting is the command that runs *first*, so a green check on a spec
   `plan` will reject is worse than no check. It now builds `AdsetSpec`s
   through the same `_dataclass_from`. Only the ad sets: requiring the ads to
   be valid would stop a researcher checking targeting before the creative
   exists, which is the ordinary order of work.
5. **`test_delete_asks_before_it_deletes` was vacuous** — a bare
   `exit_code != 0` passes just as happily when the delete went through and the
   mock's own `AssertionError` is what failed the command. It now asserts that
   no `DELETE` was made.
6. **`test_a_built_template_carries_every_field_the_runtime_reads` was half
   circular**, asserting keys `_as_meta_returns_it` constructs. Renamed to what
   it actually proves — that the builder's output survives the runtime's reader
   — and the researcher's copy is now asserted on the far side.
7. **`apply` echoed `str(FacebookRequestError)`**, which interpolates the whole
   `request_context`. No token leaks (the token is on the session's params, not
   in the context) and this prints to the user's own terminal, but it buries
   the one sentence Meta said and it inverts a convention `server/meta.py`
   states explicitly. `meta_message` now renders
   `"<message> (code N, subcode M)"`, and falls back to `str(e)` for anything
   that is not a Meta error.

The transferable one is the first: **a guard that lives inside a helper only
protects the branches that call that helper.** `build_creative` has two
branches and the validation was in one of them; the fix was to hoist it to
where every branch passes.

---

## 6. What could not be determined

**Whether the vlab Facebook app requires `appsecret_proof`.** Meta requires it
only for apps with Settings → Advanced → "Require app secret" turned on, which
is off by default. That setting is not readable from this repository, and the
conf service has never had to find out because it always holds both
`FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` (verified present on the production
deployment, plan §13.6). `adopt/scripts/ctwa_probe.py` already carried a
token-only fallback with a warning, which suggests somebody ran into the
question and did not resolve it either.

So: `api_for_token(token, app_id=None, app_secret=None)` sends the proof if and
only if an app secret is given, and the CLI warns on a token-only run naming
the exact error to expect (`code 1, Invalid appsecret_proof provided`). One
live call settles it; nothing short of one does.

**Whether `reachestimate` or `delivery_estimate` is the current edge.** Meta
has been migrating between them for years and neither this repo nor its docs
pin a version where one is gone. `validate_targeting` takes an `edge`
parameter, defaults to `reachestimate` as the brief asked, and documents
`delivery_estimate` (which additionally requires an `optimization_goal`) as
the fallback. Neither has been exercised live.

**Meta's exact read-back shape for a created creative.** The test asserts the
one assumption it makes — that `actor_id` comes back derived from
`object_story_spec.page_id` — and marks it as an assumption at
`_as_meta_returns_it`. It is documented Graph behaviour and it is the shape of
every stored template in production, but it was not verified from this branch.
`apply` warns rather than assuming, which is the whole reason the read-back
exists.

---

## 7. Known gaps

- **Nothing here has been run against live Meta**, and that is the gap that
  subsumes several below. Every shape is either lifted from a script measured
  live or taken from Meta's own documented samples; every test mocks
  `FacebookAdsApi.call`. The first live run should use a throwaway campaign
  name on the Virtual Lab account, and should be followed by deleting the
  campaign with `vlab template delete`.
- **A web or app template states no destination, so a mismatch is not
  refused.** `refuse_template_destination_conflicts` compares the
  `app_destination` values in a template's `asset_feed_spec` against what the
  conf's destination means; a web or app creative has none, so `have` is empty
  and the check returns early by design. Messenger, WhatsApp and multi
  templates *are* checked, in both directions, and `test_templates.py`
  parametrises eight mismatched pairs that must be refused. Closing the
  remaining case would mean inventing an `optimization_type` value for
  non-messaging creatives, which is guessing at Meta's enum; it is recorded
  instead.
- **Video is by id only.** `--video-id` references a video already on the
  account. There is no upload, because Meta's video upload is a resumable
  multi-request protocol rather than the single multipart POST an image is —
  a different piece of work, not a missing parameter.
- **No rollback.** A create that fails half way leaves what it already made.
  The error names the object that failed and prints the
  `vlab template delete <id>` that removes the rest. A transactional apply
  would mean deleting on failure, which is a second way to destroy things and
  needs more care than it saves.
- **`vlab template` cannot list what exists.** `vlab meta campaigns` /
  `adsets` / `ads` already do, through the server, and duplicating them here
  would be a second reader of Meta with a different credential.
- **The generated ad sets are not `reachestimate`d automatically.**
  `check-targeting --spec` does it on request; `plan` does not, because plan is
  pure and a network call in it would cost the property that makes it usable in
  CI.
- **`vlab check --live` still does not exist** (`vlab-sdk.md` §8). This
  library is adjacent to it — `find_campaign_by_name` and `validate_targeting`
  are two of the reads it would need — but it is a different command with a
  different job (checking a study that is already configured), and it is not
  started.
