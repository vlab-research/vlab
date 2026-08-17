# Ad attributions: vlab owns the ad → stratum join

**Status:** phases A1 and A2 shipped. Nothing consumes the table yet.

vlab creates exactly one ad per (creative, stratum) pair. The ad's id therefore
already determines its shortcode, its creative and its stratum metadata — which
means the dotted `ref` string vlab has historically encoded that identity into
and shipped to the survey platform inside *every message* was a redundant copy
of a fact vlab already knew.

`ad_attributions` is where vlab keeps that fact instead: a row per created ad,
mapping `(network, ad_id)` to the shortcode, creative name and stratum metadata
that ad was published with. Later phases join against it; this phase only
writes it.

## What changed, and what deliberately did not

Purely additive. **No existing study's ad-creation behaviour changes.** In
particular `make_ref` and the ref emission inside `create_creative` are
untouched, and that is a constraint rather than an oversight: reconciliation
compares creatives via `field_contract.COMPARED_AD`, so altering a creative
rewrites every ad across every live study on the next run. Existing studies keep
the dotted ref indefinitely and are never migrated.

## The data path

Everything up to the Graph API call is pure; only the last step touches a
database.

| # | Where | What happens |
|---|---|---|
| 1 | `marketing.ad_provenance` | Builds a lookup keyed by `(adset name, ad name)` — which is `(stratum id, creative name)`, because `create_adset` names an adset after the stratum and `create_ad` names an ad after its creative. Values are the `{study_id, stratum_id, creative_name, shortcode, metadata, resolved_from}` dicts destined for the table. |
| 2 | `reconciliation.adset_dif` → `ad_dif` | Stamps the matching entry onto each `"ad"`/`"create"` `Instruction` via its new optional `provenance` field. Updates and deletes get nothing — only a create learns a new id. |
| 3 | `facebook.update.GraphUpdater.execute` | Returns `(report, created_id)`. The SDK's return value used to be discarded; this is the only moment vlab ever learns the ad id without going back to the Graph API. |
| 4 | `malaria.run_instructions` → `record_ad_attribution` | Writes the row via `campaign_queries.create_ad_attribution`. |

The split at step 2/4 is the point. The `_dif` functions are the testable
functional core and stay pure — they can be exercised without a database, which
is what keeps `test_reconciliation.py` a fast unit-test file. The write lives in
the imperative shell, where the run already has a `db_conf`.

A create that carries no provenance, or whose provenance key is missing, still
succeeds — but logs a warning, because an unmapped ad is a real defect (see
below) and refusing to create the ad would be worse than creating one that is
merely unattributable.

## Three invariants

### 1. `metadata` is what `make_ref` serialises, not `stratum.metadata`

The frozen blob is `{"creative": <creative name>, **md}`, where `md` is what
`marketing.creative_metadata` builds:

```
stratum.metadata
  + study.general.extra_metadata
  + form: destination.initial_shortcode   (fly destinations only)
  + destination.additional_metadata       (if any)
```

`make_ref` prepends `creative.<creative name>`, and `form` is added at
publish time rather than declared in the stratum conf. So the ref carries
strictly more keys than `stratum.metadata` has.

Freezing `stratum.metadata` instead is the easy mistake, and it fails quietly:
the keys `creative` and `form` simply go missing. A downstream extraction conf
asking for either finds nothing, the stratum matches nobody, its count reads
zero, and the optimizer reallocates budget away from a stratum that is in fact
recruiting perfectly well. Nothing raises. Silent miscounting is the failure
mode this whole design exists to prevent, so this is the invariant to be most
careful with.

`creative_metadata` was extracted out of `create_creative` precisely so the ref
and the frozen blob are computed from one expression and cannot drift.
`test_marketing.py` also asserts the equality directly, by parsing `make_ref`'s
output back with a reimplementation of fly's own dot-pair parser
(`getMetadata`, `replybot/lib/typewheels/utils.js`) and comparing.

One known limit, asserted rather than fixed: `make_ref` does not escape `.`, so
a metadata *value* containing a dot produces a ref that parses back to garbage.
The frozen blob has no such grammar and keeps the value intact — for those
studies the ad-id path is strictly more accurate than what it replaces.

### 2. Append-only, and never rebuilt from live Facebook state

Reconciliation deletes ads that fall out of the desired set, but respondents
keep arriving from deleted ads: CTWA referrals carry
`ads_context_data.post_id`, and page posts persist and can be reshared
indefinitely. **A row must outlive its ad**, which is also why the table cannot
be reconstructed from the Graph API on demand.

Consequences visible in the schema: no TTL (unlike `study_run_events`), and **no
foreign key to `studies`** — a cascading delete is still a delete path, and this
table has none.

### 3. `metadata` is frozen at creation, permanently

Study confs mutate. A stratum's metadata today is not what it was when the ad
was created, so even a *live* ad cannot be resolved correctly by reading the
current conf. The row is a snapshot, not a pointer.

`create_ad_attribution` writes with `ON CONFLICT (network, ad_id) DO NOTHING`,
which makes this mechanical: a re-run can neither duplicate a row nor overwrite
a snapshot with today's metadata. It returns `None` when the row already
existed. **Do not add a code path that refreshes `metadata`.**

## `network` is the ad network, not the messaging channel

Messenger and WhatsApp ads are both Meta ads living in one id namespace, so both
are `facebook`. The discriminator exists because Meta ad ids are only unique
within Meta and TikTok/Google Ads are already contemplated — it is much cheaper
to add before a second network exists than after. Easy to get backwards.

`resolved_from` records which id source produced the row: `'ad_id'` for rows
written at ad creation (all of them today), leaving room for a row resolved from
a WhatsApp referral's `source_id` to be distinguishable later without
archaeology.

## Failure mode to watch

An ad created with no mapping row can never be attributed, and **there is no
backfill path** — the design rejected retrofitting existing studies. For that
reason `record_ad_attribution` raises on a failed write rather than continuing:
stopping the run leaves the remaining ads uncreated, which the next run fixes,
whereas carrying on would mint permanent silent gaps. `run_updates` already
catches per-study, so one study's failure does not stop the others.

This is also why **A1 and A2 must be in production before the first ad of any
study that opts into ad-id attribution.**

## Where things live

| Thing | Path |
|---|---|
| Migration | `devops/migrations/20260816000000_add_ad_attributions.{up,down}.sql` |
| Schema bootstrap (second copy — keep in sync) | `devops/helm/migrations/init.sql` |
| Provenance construction | `adopt/adopt/marketing.py` |
| Instruction plumbing | `adopt/adopt/facebook/{update,reconciliation}.py` |
| Write path | `adopt/adopt/{malaria,campaign_queries}.py` |
| Integration tests (need `make test-db`) | `adopt/adopt/test_ad_attributions.py` |
| Invariant + purity tests | `adopt/adopt/test_marketing.py`, `adopt/adopt/facebook/test_reconciliation.py` |

Full design, including the later phases (first-class `ad_id` on
`InferenceDataEvent`, swoosh's `location: "ad"` extraction, unmapped-ad
counters, and the per-study lever that finally retires the ref):
`planning/ad-id-attribution.md`.
