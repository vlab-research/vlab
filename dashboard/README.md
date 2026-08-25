# VLABS Dashboard

## Getting Started

### Install Dependencies

```bash
npm install
```
### Setup Local TLS

due to some configurations needed with facebook we need to use HTTPS in our
local environment. We use [mkcert][1] to handle this so please **install
mkcert**

You can then run:
```bash
make certs
```

and this will setup your local certificate setup

### To start the application

You will need to configure your local environments, to start copy the
`.env-example` to `.env` and fill in any missing values 

```bash
npm start
```
Runs the app in the development mode.
Open [https://localhost:3000](https://localhost:3000) to view it in the browser.

The page will reload if you make edits.
You will also see any lint errors in the console.

### Running Tests

To run the unit tests

```bash
npm test
```
Launches the test runner in the interactive watch mode.
See the section about [running tests][3] for more information.

To run the E2E tests using Cypress you will need to copy the
`cypress.env.json.example` => `cypress.env.json` and update it with valid
values

We currently run Cypress with our backend so you will need to start this by
navigation to the [api](../dashboard-api) directory and running:

```bash
make dev
```
>Note this is under the assumption that you have setup the backend
accordingly, please read thee backends [README](../dashboard-api/README.md) for
more details

Once your backend is up and running you can run the following to start your
cypress tests

```bash
npm run cypress
```
This requires you to be [running the frontend](#to-start-the-application)

**NOTE:** the cypress tests  will create resources, if you want to run them
again you will need to reset the seed data, you can do this in the
[api](../dashboard-api) directory by running:

```bash
make reset-seed
```

### Building the application

```bash
npm run build
```
Builds the app for production to the `build` folder.
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.
Your app is ready to be deployed!

See the section about [deployment][2] for more information.


[1]: https://github.com/FiloSottile/mkcert#installation
[2]: https://facebook.github.io/create-react-app/docs/deployment
[3]: https://facebook.github.io/create-react-app/docs/running-tests

## Study-conf forms: the ad-attribution halves

Two questions about a recruitment ad's ref, and they are independent. What the
ref carries is `ref_mode`, on a destination; what a value read means is
`mapping`, on an extraction conf. Neither side validates, gates or reads the
other — they are separate confs, POSTed to separate endpoints, each saving on
its own terms in any order.

Both follow the same split as `forms/variables/extract.ts`: a pure module with
no React dependencies, testable in isolation, plus a thin component wiring that
module's helpers to `Select`/`TextInput` fields.

### The ref-mode control

`forms/destinations/refMode.ts` is the pure module and `RefModeField.tsx` the
control, rendered by all five destination forms — Messenger, WhatsApp, Multi,
Web and App. One control rather than a copy each, so that a multi-channel study
attributes exactly one way. `refModeOptions()` takes no arguments and returns
both modes: what a ref carries is a property of the ref, not of the channel
carrying it, so there is nothing to decide it from.

It labels by consequence. The words `ref_mode` and `encoded` never reach the
screen — what a researcher needs to decide is where their stratum data ends up
and what the key is: inline, so the export already has `gender` and `region` as
columns and there is nothing to join; or looked up afterwards from the
ad-attributions export.

**The rule that carries the migration.** The encoded default is a *new-conf*
affordance and is never written onto a conf that arrived without one. An absent
`ref_mode` is a real state: the conf predates the field, and resolves to the
behaviour it already has. Writing a mode onto such a conf would rewrite that
study's ads on the next reconciliation run for no reason anyone asked for.
Three properties hold it, and all three are required:

1. `displayedRefMode(stored) = stored || "metadata"` reports what a conf
   actually does, and is never written back.
2. The default lives only in the two empty-state constructors —
   `Destination.tsx` `emptyStates` and `Destinations.tsx` `initialState` — both
   of which build new confs. Every type gets it, web and app included.
3. The forms spread `...data`, so a field absent from a conf stays absent
   through an unrelated edit.

`Destination.test.tsx` pins the scenario these exist for: open a destination
with no `ref_mode`, edit its welcome message, save, and the saved conf still has
no `ref_mode`. Keep it passing.

Changing a **saved** destination's mode warns. The ref is part of the creative
and reconciliation compares creatives, so a change rewrites every ad in the
study on the next run: real spend, possibly another Meta review, and the
learning phase starting over. Live posts people have shared start pointing at
the new link. Existing respondents keep their attribution. The comparison runs
through `displayedRefMode`, so absent and an explicit `"metadata"` count as the
same thing — they describe the same ads. The warning is driven by the *saved*
conf, so a destination being added now never warns.

### The extraction form

`forms/inferenceData/extraction.ts` is the pure module and `Extraction.tsx` the
component, serving fly, Qualtrics and Typeform alike.

An extraction conf says where to find one variable's value in two parts.
`location` says **where to read**: `variable` (walk a path into the respondent's
response payload) or `metadata` (look up a key in what the connector stamped on
the event). `mapping` says **what the value read means**: `raw` (it IS the
answer — the default, and what every conf written before this field existed
means) or `ad_table_lookup` (it is an opaque token identifying the ad that
recruited the respondent, and the answer is a stratum variable off that ad's
frozen `ad_attributions` row).

There is no `ad` location. There never really was one — the old `location:
"ad"`, which joined on `ad_id`, has been removed.

**Every source offers both locations and both mappings.** The fly and Qualtrics
forms used to be separate modules, on the reasoning that only fly carries a
token. That does not hold: a respondent recruited by a web or app destination
lands on the researcher's own page and brings the token back as a Typeform or
Qualtrics field. All that a source still decides is which response values its
payload offers — `responseOptions`, a fly event's answer and its translation
against a survey answer's label and value.

Changing the location leaves the mapping alone, since location says nothing
about what was read.

`metadata` is a *keyed* read under either mapping — you name a key and get a
value — while `variable` is the only one with a response path to select. That
distinction is expressed once, as `isKeyedLocation`, rather than as scattered
`=== "metadata"` checks through the form. The same split drives `aggregate`:
keyed locations get `"first"`, because they are recruitment-time constants —
you attribute someone to the ad and metadata they arrived with. Only `variable`
gets `"last"`, since a survey answer is the only one that can meaningfully be
updated later. `applyChange` derives `aggregate` from the conf's own location on
every change rather than pinning it to `"first"`: pinned, an edit to any other
field would quietly demote a `variable` conf back to the first value it ever
saw.

**Both text fields change meaning under a lookup**, and the form's prompts say
so, because getting them backwards is the easy mistake:

| Field | Raw read | Ad lookup |
|---|---|---|
| `key` | the key or field holding the value | the key or field holding the **token** — `vt` on fly |
| `name` | what to call the variable | the **stratum variable** to pull (`creative`, `gender`, `Age`), which is also what it is called |

### Read-side defaults

`generateLookupConfs.ts`. A fly source with nothing saved starts with one
`ad_table_lookup` conf per variable declared in Variables, in place of a single
blank row. The researcher already named those variables and the name is exactly
what the ad's frozen row is keyed by, so asking for them again in a different
vocabulary is what produces silent half-configs.

A default, not a merge: a source with saved confs shows those, a source without
shows these, nothing merges, and no second copy is held anywhere. It is consumed
in `InferenceData.tsx`, where `initialState` is already built per source.

Fly only, because the default has to guess where the token is and `vt` is fly's
convention; another source returns it as a field only the researcher can name.

### The Ad Attributions step

`forms/adAttributions/` renders the study's ad -> stratum mapping as a table,
with a CSV download, from adopt's `ad_attributions_table`. The CSV is rendered
from the rows the table is showing rather than fetched separately, so a file
saved from the page and the page itself cannot show different columns — and
adopt serves identical bytes at `/{org}/studies/{slug}/ad-attributions.csv` for
a script doing the join.

It is registered in `shared.ts`, whose `confs` array doubles as the wizard's
next-step chain via `getNextConf` — so adding a step changes where the previous
one advances to.

See `documentation/ad-attributions.md` for the mechanism this feeds.

Tests: `forms/inferenceData/extraction.test.ts`,
`forms/destinations/refMode.test.ts`, `forms/destinations/Destination.test.tsx`
and `forms/adAttributions/adAttributions.test.ts`, run with `npm test`.
