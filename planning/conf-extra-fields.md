# `extra="ignore"` on every conf model — investigation, and the fix

Status: **IMPLEMENTED, 2026-09-05** (adopt v0.1.85). §1–§6 below are the
original investigation, left as written; §7 records what shipped, what §6's two
open questions were settled to, and the one thing the investigation missed.
Read §7 first if you are here to find out what the code does now.

Originally written for
`planning/agent-study-authoring.md` §11.4 item 2 / §11.5, which flags this as
the defect that most needs settling before Phase 3 (the SDK) starts: an SDK
that validates locally is worth much less if the server silently drops what it
does not recognise.

Scope note: this document does **not** touch `InvalidConfigError` deriving
from `BaseException` — that was Task 1 of the same job and was fixed
separately (see the class docstring at `adopt/adopt/study_conf.py:930` and the
PR this doc ships alongside). This doc is Task 2: `extra="ignore"` only.

All file:line references below are relative to this worktree
(`/home/nandan/Documents/vlab-research/vlab/.claude/worktrees/conf-validation-fixes`)
and were verified by reading the cited lines directly, not taken on faith from
grep output alone.

---

## 1. Finding: nothing sets `extra=` explicitly, anywhere

`grep -n "extra=" adopt/adopt/study_conf.py adopt/adopt/*.py adopt/adopt/facebook/*.py adopt/adopt/server/*.py`
returns zero hits. The only `model_config` in `study_conf.py` is on
`CreativeConf` (`study_conf.py:895`, `ConfigDict(arbitrary_types_allowed=True)`
— unrelated to extra-field handling). Every model in the file therefore runs
on pydantic v2's default, `extra="ignore"`.

`RefModeDestination` (`study_conf.py:133-145`, the base class for every
destination type) is the one place that already says why, in its own
docstring:

> Unknown keys are tolerated, which is pydantic's default and is relied on
> here: confs are stored as raw JSON and read back through the model, so
> forbidding extras would stop every conf written before any future field
> removal from loading, and halt that study's reconciliation.

No other model has an equivalent comment, but the same mechanical reasoning
applies to all of them, because of how loading works — see §2.

`FacebookTargeting` is **not** a pydantic model that could have this problem:
`study_conf.py:878` defines it as `FacebookTargeting = Dict[str, Any]`, so it
is arbitrary-key by design, not via the extra=ignore default. `QuestionTargeting`
lives in the same file (`study_conf.py:107`), not imported from elsewhere.

The full class list in `study_conf.py`, for reference: `DataSourceConf:16`,
`ExtractionFunctionConf:23`, `ExtractionConf:35`, `SourceExtractionConf:84`,
`InferenceDataConf:89`, `UserInfo:93`, `TargetVar:102`, `QuestionTargeting:107`,
`RefModeDestination:133`, `FlyMessengerDestination:159`, `WebDestination:168`,
`AppDestination:177`, `FlyWhatsAppDestination:323`, `FlyMultiDestination:389`,
`BaseRecruitmentConf:591`, `SimpleRecruitment:634`,
`PipelineRecruitmentExperiment:698`, `DestinationRecruitmentExperiment:800`,
`GeneralConf:884`, `CreativeConf:894`, `StratumConf:903`, `Level:916`,
`VariableConf:924`, `Partitioning:978`, `SimpleRandomizationConf:1026`,
`RandomizationConf:1030`, `LookalikeSpec:1042`, `Lookalike:1048`,
`AudienceConf:1053`, `Audience:1073`, `LookalikeAudience:1079`, `Stratum:1088`,
`StudyConf:1103`. (Line numbers current after the Task 1 edit, which added
~30 lines of docstring at `InvalidConfigError`, now at `study_conf.py:930`.)

## 2. Every write-time model except one is *also* a load-time model, through the identical class

`get_study_conf` (`adopt/adopt/malaria.py:58-65`):

```python
confs = get_campaign_configs(study_id, db_conf)
cd = {v["conf_type"]: v["conf"] for v in confs}
params = {"id": str(study_id), "user": user_info, **cd}
return StudyConf(**params)
```

`get_campaign_configs` (`adopt/adopt/campaign_queries.py:86-98`) pulls the
latest row per `conf_type` from `study_confs` (a `ROW_NUMBER() OVER (PARTITION
BY conf_type ORDER BY created DESC)` window query, `n = 1`) — literally the
same JSON blob each `POST /confs/{conf_type}` wrote (`server.py:115-122`,
`config.model_dump()`), fed straight back into `StudyConf(**params)`.

`StudyConf`'s fields (`study_conf.py:1103-1116`) are typed with the exact
classes the POST routes use: `general: GeneralConf`,
`destinations: list[DestinationConf]`, `audiences: list[AudienceConf]`,
`creatives: list[CreativeConf]`, `strata: list[StratumConf]`,
`recruitment: RecruitmentConf`, `inference_data: Optional[InferenceDataConf]`,
`data_sources: Optional[list[DataSourceConf]]`. All eight are genuinely
dual-use (write *and* load) through the identical class — there is no
separate "load" schema today.

`get_study_conf_for_reports` (`malaria.py:551-576`, the report-healing cron
added since §2.5 of the parent doc was written) does the same `StudyConf(**params)`
construction from the same `cd` shape at line 576, so it carries the identical
exposure.

**One exception: `VariableConf`** (`study_conf.py:924`; `POST /confs/variables`
at `server.py:175-182`) is **not** a field of `StudyConf` at all — confirmed
directly: there is no `variables:` line in the `StudyConf` class body
(`study_conf.py:1103-1116`), and `grep -n "variables" study_conf.py malaria.py`
turns up nothing that reconstructs a `VariableConf` from storage. It is
written and read back only through `get_conf`/`get_all_confs` — raw JSON
passthrough (`server/db.py`), never re-validated through pydantic on read, by
any conf_type. So `VariableConf` is the one model where a stricter write-time
variant costs nothing on the load path, because there is no load path for it.

**Consequence for a fix**: "forbid on write, ignore on load" is not a
different *model* for most conf types today — it would have to be a different
*class* used only by the POST route, because the load path needs the lenient
one to keep loading confs written before a field was added or renamed. Only
`VariableConf` could take `extra="forbid"` directly, with no sibling class
needed.

## 3. Dashboard payloads vs pydantic fields, section by section

`useCreateStudyConf.tsx:9-24` takes `data: any` and passes it straight through
to `createStudyConf({ data, studySlug, confType })` — no field-picking, no
mapping layer. Whatever object lives in the React form's local state **is**
the POST body, verbatim. So the question is entirely "what does each form's
local state contain."

- **Destinations** — clean. `forms/destinations/Destination.tsx:41-82`
  defines one `emptyStates[]` object per destination `type`;
  `handleSelectChange` (lines 86-91) **fully replaces** the data object with
  the fresh `emptyStates` entry on a type switch (`updateFormData(fields,
  index)`, not a merge), so a field left over from a previously chosen type
  cannot survive a switch. Checked field-for-field against
  `dashboard/src/types/conf.ts` and `study_conf.py`: Messenger
  (`conf.ts:65-73` vs `FlyMessengerDestination`, `study_conf.py:159-166`, plus
  `ref_mode` from the `RefModeDestination` base at `study_conf.py:151`), Web
  (`conf.ts:75-79` vs `WebDestination`, `study_conf.py:168-175`), App
  (`conf.ts:80-90` vs `AppDestination`, `study_conf.py:177-186`), WhatsApp
  (`conf.ts:96-104` vs `FlyWhatsAppDestination`, `study_conf.py:323-349`),
  Multi (`conf.ts:112-121` vs `FlyMultiDestination`, `study_conf.py:389-444`).
  No extra-field mismatch in any of the five. The 2026-08-30 incident
  documented at `study_conf.py:496-535` — a multi conf silently resolving to
  `FlyMessengerDestination` under the old shape-matched union, with
  `whatsapp_phone_number` accepted and ignored as an extra — is closed by the
  discriminator, and the current dashboard form shape does not reopen it.
- **Audiences** — `forms/audience/Audience.tsx:12-56` renders only a `name`
  input; "Selected respondents only" is disabled in the UI with
  "(not yet available)" (lines 41-47). `forms/audience/Audiences.tsx:29-33`
  hardcodes `initialState = [{ name, subtype: 'CUSTOM' }]`. The dashboard
  never constructs a `LOOKALIKE` or `PARTITIONED` audience today, so
  `lookalike` / `partitioning` / `question_targeting` (all optional on
  `AudienceConf`, `study_conf.py:1053-1057`) are never sent. That is an
  *omission* of optional fields, not the extra-field problem this doc is
  about — but it means the dashboard has never exercised the write path this
  investigation is worried about for audiences.
- **Creatives** — `forms/creatives/Creatives.tsx:37-42` builds `{name,
  destination, template, template_campaign}`, matching `CreativeConf`
  (`study_conf.py:894-900`) minus the optional `tags`. `tags` is referenced
  nowhere in `Creative.tsx`/`Creatives.tsx`; `conf.ts`'s `Creative` type
  (lines 121-126) also omits it. Omission, not extra.
- **Strata** — `forms/strata/Stratum.tsx:33-51` drives `id`, `quota`,
  `creatives`, `audiences`, `excluded_audiences` (with
  `facebook_targeting`/`question_targeting`/`metadata` handled in the same
  file), matching `StratumConf` (`study_conf.py:903-913`). No mismatch found.
- **General** — `conf.ts`'s `General` type (lines 4-10) omits
  `extra_metadata` (`GeneralConf`, `study_conf.py:891`, defaults to `{}`).
  Omission, not extra.

**Conclusion**: the dashboard is field-aligned with the pydantic models
*today*, but by convention (careful `emptyStates` objects and hand-written TS
types kept in sync by hand), not by any enforced contract. The residual risk
`extra="ignore"` protects against is not "the dashboard already sends garbage"
— it doesn't — it is (a) a future dashboard change drifting from the models
unnoticed, and (b) an agent authoring JSON directly, which is exactly the
Phase 3 subject: an agent has no `emptyStates` object to copy and no
compile-time TS check: a misspelled or renamed field gets `201` and is
silently discarded.

## 4. A safe shape, and why it's the recommendation

Checked directly (`model_validate(payload, strict=True)` on a plain model
raises nothing for an extra key): `strict=` does **not** control `extra`
handling in pydantic v2. `extra` is controlled solely by
`ConfigDict(extra=...)` on the class. That rules out "just pass
`strict=True`" as a shortcut.

**Option 1 — strict sibling classes, swapped into the POST route type
annotations only.** E.g. `class GeneralConfStrict(GeneralConf):
model_config = ConfigDict(extra="forbid")`, used as the `config:` parameter
type on `create_general_conf` and friends in `server.py`, in place of the
base class. `create_conf` (`server.py:115-122`) already treats the config
generically via `.model_dump()`, so no handler-body changes are needed —
only the annotation on each route function, plus one new subclass per model.
`load_basics`/`get_study_conf`/`StudyConf` keep using the base lenient
classes, untouched, preserving the forward-compatibility guarantee
`RefModeDestination`'s comment documents.

The non-trivial part is `DestinationConf`, a `Field(discriminator="type")`
union (`study_conf.py:526-540`): a strict variant needs a parallel
discriminated union built from strict destination subclasses, used only by
the `/confs/destinations` route. `VariableConf` needs no parallel lenient
class at all (§2 — it is never reloaded) and can simply take
`extra="forbid"` directly, no sibling required.

**Option 2 — diff payload keys against `model_fields` and 422 naming the
unknown keys**, as a shared dependency/decorator. This requires accepting the
raw JSON body (`dict`/`Request`) at each route rather than a typed
`config:` parameter, because once FastAPI has built the model the dropped
keys are already gone — there's nothing left to diff. That means changing
every route's parameter signature, and adding an explicit
`Model.model_validate(raw)` call plus a key-diff inside each handler: a
larger, more invasive touch to `server.py` than Option 1, and one that would
duplicate FastAPI's existing request-parsing machinery rather than reusing it.

**Recommendation: Option 1** — strict sibling classes on the POST routes
only. Lower blast radius (annotation-only change per route, zero change to
`load_basics`/`get_study_conf`/`StudyConf`/handler bodies), and it reuses
FastAPI's existing request-validation pipeline (which, after the Task 1 fix,
now correctly turns a validation failure into a 422 with the message intact)
rather than building a parallel one.

**Dependency worth calling out**: `RecruitmentConf` is an untagged,
shape-matched union (`agent-study-authoring.md` §11.4 item 3 — the same
defect class the destination union had before 2026-08-30, per the comment at
`study_conf.py:1090`). Building a strict variant of an already-ambiguous union
does not fix the ambiguity underneath it — that item should probably be
settled (tagging the union) before or alongside a strict `RecruitmentConf`
sibling is built, or the "strict" version just forbids typos while still
silently mis-resolving a legitimately-typed-but-under-specified body to the
wrong arm.

## 5. Do NOT query production — but here is the query that would tell someone

This investigation did not, and should not, touch production data. If a
follow-up wants to know how many *already-stored* confs would break under
`extra="forbid"` (to decide how aggressively to roll it out, and whether any
need a one-time cleanup first), the shape of that query is:

1. Pull the latest row per `(study_id, conf_type)` from `study_confs` using
   the window-function query already at `campaign_queries.py:86-98` (or its
   twin at `server/db.py`) — do not write a new one.
2. In Python, per `conf_type`, diff the stored JSON's keys against that
   section's current `Model.model_fields` — recursing into list elements for
   the conf types that are lists (`destinations`, `creatives`, `strata`,
   `audiences`, `variables`, `data_sources`).
3. Count and name which studies/conf_types carry keys outside today's model —
   that count is what should gate how aggressively `extra="forbid"` rolls out
   (a nonzero count for a given conf_type means some stored data needs
   attention before that type goes strict, even for Option 1's write-only
   change, because a later edit-and-resave of that same conf through the
   strict route would now fail on a field it used to tolerate).

## 6. Open questions

*(Answered in §7.2 and §7.3.)*

1. Is there a non-dashboard writer of these confs that could be carrying
   forward legacy/extra keys? Two candidates: the notebook era
   (`~/Documents/vlab-research/campaigns/*.ipynb`, per
   `agent-study-authoring.md` §4 — outside this repo, not checked here), and
   `copy_confs` (`server/db.py`, referenced from `server.py:219-227`), which
   copies stored JSON verbatim between studies and would happily propagate an
   old extra key from a source study into a new one.
2. Should a strict destination union also reject a *missing* `type`? The
   `_default_missing_destination_type` `BeforeValidator`
   (`study_conf.py:478-493`) fills in `"messenger"` for legacy confs with no
   `type` at all. On a **fresh write** — which is all the strict route ever
   sees — a missing `type` is far more likely an authoring mistake than
   legacy data, so the strict variant may want to skip that default entirely
   rather than reuse it.

---

## 7. What shipped

Option 1, as recommended, with three decisions the investigation left open and
one correction to it.

### 7.1 The shape

`adopt/adopt/study_conf_strict.py`: an `XStrict(X)` twin per write-time model,
each carrying `model_config = ConfigDict(extra="forbid")`, swapped into the
nine POST route annotations in `server.py`. No handler body changed.
`load_basics` / `get_study_conf` / `StudyConf`, and the `StratumConf` rebuild in
`get_recruitment_stats`, keep the lenient classes — the forward-compatibility
guarantee `RefModeDestination`'s docstring describes is untouched.

**Strictness is recursive.** `extra="forbid"` on an outer class does nothing for
the models nested inside it, so every model reachable from a route has a twin
and every field pointing at one is re-declared to point at the twin. A typo at
`levels[].facebok_targeting` is as likely as one at the top level and was
exactly as silent. Because that re-declaration is the step a future change will
forget,
`test_study_conf_strict.py::test_every_nested_model_reachable_from_a_route_is_strict`
walks annotations out from each route's type and fails on any model it reaches
that is not strict.

Arbitrary-key fields stay arbitrary — `FacebookTargeting` and
`FacebookAdCreative` hold Meta's spec objects, and `extra_metadata` /
`metadata` / `additional_metadata` hold user-chosen keys. Forbidding an unknown
key there would forbid the feature.

**`VariableConf` got a twin too**, though §2 licensed forbidding in place
because nothing reloads it. That licence rests on a fact about today, not a
property of the model, and a `POST /studies/{slug}/validate` endpoint that
re-reads stored confs was being built alongside this. One uniform mechanism
costs four lines and removes the need to remember which model is the exception.

### 7.2 §6 question 1: partly answered, and the investigation missed the real risk

§3 checked the dashboard's **forms** against the models and found them aligned.
That was the wrong place to look. What round-trips through the dashboard's
**edit** path is *stored JSON*, re-POSTed verbatim (`useState(localData ? ...)`)
— and stored JSON is the last successful `model_dump()`, so it contains whatever
the models declared on the day it was last saved, including fields since
removed.

Two such fields exist, both provable from git:

| Key | Was | Removed |
|---|---|---|
| `recruitment.destination_type` | REQUIRED on all three arms | `d382000c`, 2026-08-30 |
| `destinations[].include_metadata_in_ref` | required on the destination base | `065bacb8`, 2026-08-24 |

Every recruitment conf older than 2026-08-30 carries `destination_type`, so a
naive `extra="forbid"` would have turned "extend a study's end date" into a 422
across the corpus. Both are now on a **closed list of retired keys**, accepted
and stripped before validation — exactly the behaviour they have had since the
day they were removed. Naming them rather than leaving `extra="ignore"` on is
the whole point: two names citable to a commit is a bounded set; every possible
misspelling is not. A future field removal adds a line there or breaks the
dashboard's edit path.

The rest of question 1 is still open and needs §5's production query, which was
deliberately not run. If the notebook era or `copy-from` left some other key in
the corpus, it is now a 422 on that conf's first re-save, naming the key — which
is recoverable (add the name) and, unlike the old behaviour, visible.

One live dashboard bug also surfaced, unrelated to retired keys: the
recruitment form's destination-experiment `initialState` carried
`destination: ''` — singular, a leftover, never a field on
`DestinationRecruitmentExperiment`. Fixed in the dashboard rather than
tolerated, because it is a bug and not history.

### 7.3 §6 question 2: settled — the strict union KEEPS the legacy default

The strict destination union applies `_default_missing_destination_type`, the
same validator the lenient one uses, shared rather than copied.

This was decided the other way first, on the argument §6 itself suggests: a
fresh write never predates the `type` field, so a missing tag is an author who
forgot it, and defaulting it hands them a destination they did not ask for. The
argument does not survive contact with `extra="forbid"`, and the reason is the
part worth keeping.

A typeless payload is defaulted to `messenger` and *then validated against the
strict messenger twin*. Anything that is not genuinely messenger-shaped carries
fields messenger does not declare, and those are now unknown keys. Measured,
per shape:

| Typeless body | Result |
|---|---|
| messenger-shaped | accepted, stored as `type: "messenger"` |
| whatsapp-shaped | 422 — `whatsapp_phone_number` extra, `button_text` missing |
| **multi-shaped** | **422 — `whatsapp_phone_number` extra** |
| web-shaped | 422 — `url_template` extra, three fields missing |
| app-shaped | 422 — six extras, three missing |

The multi row is the whole argument. That is the 2026-08-30 incident shape: it
satisfies *every* field a Messenger destination requires, so no required-field
check and no mandatory tag could distinguish it — it is caught solely by
`whatsapp_phone_number` being an unknown key. **Forbidding extras is what closed
that hole; requiring the tag was never what closed it.** So the default can only
ever admit a payload that really is a messenger destination, which is the
correct result rather than a silent mis-resolution.

What the 422 did cost was real. The 45 typeless confs across 11 studies
round-trip through the dashboard, which renders no subform for a destination
whose type it cannot read and re-POSTs the conf verbatim. Refusing them makes
editing destinations impossible on those studies, and whether any of them is
live was not determined. Production breakage for zero added protection is not a
trade worth making.

The committed schema still marks `type` required, deliberately: an agent
authoring new configuration should write the tag, and the file being stricter
than the server on this one key is the right direction. `adopt/README.md` says
so under "what the schemas do not say".

### 7.4 The dependency in §4 was real, and was taken first

§4 warned that building a strict variant of the already-ambiguous
`RecruitmentConf` would forbid typos while still mis-resolving an
under-specified body. So the union was tagged first, on `type`, following the
destination precedent: a literal per arm, a BeforeValidator inferring the tag
from shape for stored confs, `Field(discriminator=...)`.

The tag values — `simple`, `pipeline_experiment`, `destination` — were not
invented. The dashboard has been sending exactly those strings in a `type` key
all along; `extra="ignore"` was eating them. §3 did not check the recruitment
form, which is how that went unnoticed.

The strict recruitment union **keeps** the shape inference, unlike the
destination one. Every stored recruitment conf reads back untagged (the tag was
dropped before storage), and the dashboard's edit path re-POSTs it, so
requiring the tag would 422 every edit of every study. Nothing is lost:
`extra="forbid"` is what makes an over-specified body a 422 naming
`destinations` instead of a silent downgrade to the pipeline arm, which is what
§11.4 item 3 actually asked for. The inference becomes removable once every
stored conf carries a real tag, which `model_dump()` now writes.

### 7.5 A bug found on the way

`LOOKALIKE` and `PARTITIONED` audiences could never be written as JSON at all —
`AudienceConf.__post_init__` runs at `mode="before"` but required the
sub-object to be an already-parsed `Lookalike` / `Partitioning`. Found because
the strict twins for those two models had no reachable code path to test
against. Fixed (presence check only; shape is the field annotation's job) and
recorded as `agent-study-authoring.md` §11.4 item 7.

### 7.6 What §5 still buys

The production query in §5 was not run and is still the right thing to run. It
no longer gates the rollout — the retired-key list handles the two failures git
can prove — but it is the only way to know whether anything *else* is out there
before someone meets it as a 422.
