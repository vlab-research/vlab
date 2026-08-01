# Verifying the field contract fix in production

What "working" looks like after `adopt` v0.1.77 rolls out, and how to check it.

The short version: **ads should stop updating almost entirely; adsets should
keep updating, but only when the optimizer actually moves money.** If ad
updates are still happening on every run, the fix did not land.

## Measured baseline (before the fix)

From a real `vlab-adopt-ads` run on v0.1.75/76, captured 2026-07-29:

```
Generated 36 instruction(s) for OWIS Nigeria Study
Generated 2 instruction(s) for Girl Effect

ad updates:                 30
adset updates:               8
creative mismatch warnings: 30
```

That was every run, every two hours: **38 write instructions, ~456 a day.**

Not all of it was waste. Of the 8 adset updates, 7 were genuine optimizer budget
moves. One was not:

```
_eq: mismatch at .daily_budget — desired='100' source=100
```

Same number, flagged only because Facebook returns a string and we send an int.
That stratum sits at `min_budget`, so its budget never changes — it was rewritten
on every run, forever, for nothing.

All 30 ad updates were waste.

## What to expect after

| | before | after | note |
|---|---|---|---|
| ad updates per run | 30 | **0** | when no creative or config changed |
| adset updates per run | 8 | **~7** | only genuine budget moves; varies by run |
| `creative mismatch` warnings | 30 | **0** | |
| total instructions per run | 38 | **~7** | roughly an 80% reduction |

Adsets will *not* go to zero and should not be expected to. The optimizer
recomputes budgets every run and they rarely land on the same number. What
should disappear is the adset whose budget did not change — anything pinned at
`min_budget`, and any run where the optimizer holds steady.

Ads should be flat zero on a run where nobody edited a study. A single ad update
after a real creative edit is correct — it should then be followed by zero on the
next run. **An ad update repeating across consecutive runs is the failure
signal.**

## How to check

The `adopt-ads` cron runs `30 */2 * * *`. Give it two or three ticks.

```bash
# newest completed adopt-ads pod
POD=$(kubectl get pods -n vprod --no-headers --sort-by=.metadata.creationTimestamp \
  | grep '^vlab-adopt-ads-' | tail -1 | awk '{print $1}')

kubectl logs "$POD" -n vprod > /tmp/adopt-ads.log

# the headline numbers
grep -E "Generated [0-9]+ instruction" /tmp/adopt-ads.log
echo "ad updates:    $(grep -c 'Executing: ad/update'    /tmp/adopt-ads.log)"
echo "adset updates: $(grep -c 'Executing: adset/update' /tmp/adopt-ads.log)"
echo "mismatches:    $(grep -c 'creative mismatch'       /tmp/adopt-ads.log)"
```

Pass condition, on a run where no study was edited:

- `ad updates: 0`
- `mismatches: 0`
- `adset updates` ≤ the number of strata whose budget genuinely moved

Compare across **three consecutive runs**, not one. One run tells you little; the
same 30 ads updating three times running is the bug still present.

### The new warning to watch for

```bash
grep 'undeclared drop' /tmp/adopt-ads.log
```

This is the fix's own alarm. It means we sent a field Facebook did not echo back,
and it is not in `field_contract.DROPPED`. Expect **none**. If one appears:

1. It names the exact path.
2. Run `adopt-probe <study>` to confirm against live data.
3. Decide whether it is a genuine drop (declare it) or a real change that should
   be applied once (leave it alone — it will converge on the next run).

Do not reflexively `--update`. A genuine one-time change looks identical to a
drop; `planning/field-contract.md` has a worked example
(`targeting.targeting_automation`) where declaring it would have been wrong.

### Facebook API pressure

The loops were a contributing cause of `code 17 / Ad Account Has Too Many API
Calls` throttling. With ~80% fewer writes, backoff should become rarer:

```bash
grep -c 'Too Many API Calls' /tmp/adopt-ads.log     # expect 0, was 4
grep -c 'Backing off'        /tmp/adopt-ads.log
```

This is a secondary signal — rate limiting depends on everything else touching
the ad account too, so treat a non-zero count as worth a look rather than a
failure.

### Direct check with the probe

Independent of the logs, and read-only:

```bash
kubectl port-forward -n vprod svc/gbv-cockroachdb-public 5432:26257 &

cd adopt
set -a; source .env; set +a
export PG_URL='postgres://root@localhost:5432/vlab?sslmode=disable'

poetry run adopt-probe "OWIS Nigeria Study"    # expect exit 0, "contract matches"
poetry run adopt-probe "Girl Effect"           # expect exit 0
```

Point it at **active** studies only. An inactive study can never report clean —
`end_time` is a rolling 48-hour window, so its frozen adsets always look behind.

## What would mean it is not working

| symptom | reading |
|---|---|
| ad updates > 0 on three consecutive runs, same ad names | a dropped field is still undeclared — check for `undeclared drop` |
| adset updates on a run where no budget changed | a representation mismatch is unhandled; run the probe |
| `undeclared drop` on an active study | Facebook's behaviour moved; investigate before declaring |
| ads updating that were *not* updating before | the fix broke something — see rollback |

## Rollback

Nothing here changes what adopt sends to Facebook — only whether it decides to
resend it. The failure mode is "still writes too much", not "writes something
wrong". So rollback is not urgent, and is a one-line values change:

```bash
# devops/values/toixo-prod.yaml
versionAdopt: &vadopt v0.1.76      # from v0.1.77

helm upgrade vlab devops/helm -f devops/values/toixo-prod.yaml -n vprod
```

The one genuine behaviour risk is the opposite direction: a change that *should*
be applied being treated as already-applied. The guards for that are
`test_ad_dif_updates_when_object_story_spec_format_changes` and
`test_update_adset_still_applies_a_newly_added_audience`. If a study edit stops
taking effect in production, that is the thing to suspect, and it is worth
rolling back for.
