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

## Inference-data extraction forms

The extraction-conf forms under
`src/pages/StudyConfPage/forms/inferenceData/` follow the same split as the
existing `forms/variables/extract.ts`: a pure module with no React
dependencies, testable in isolation, plus a thin component that just wires
that module's helpers to `Select`/`TextInput` fields. `flyExtraction.ts` and
`qualtricsExtraction.ts` are the pure modules; `FlyExtraction.tsx` and
`QualtricsExtraction.tsx` are the components that consume them.

An extraction conf says where to find one variable's value in two parts.
`location` says **where to read**: `variable` (walk a path into the
respondent's response payload) or `metadata` (look up a key in the metadata fly
stamped on the event). `mapping` says **what the value read means**: `raw` (it
IS the answer — the default, and what every conf written before this field
existed means) or `ad_table_lookup` (it is an opaque token identifying the ad
that recruited the respondent, and the answer is a stratum variable off that
ad's frozen `ad_attributions` row).

There is no `ad` location. There never really was one — the token lives in
metadata, so reading it is an ordinary metadata read — and the old `location:
"ad"`, which joined on `ad_id`, has been removed.

`metadata` is a *keyed* lookup under either mapping — you name a key and get a
value — while `variable` is the only one with a response path to select. That
distinction is expressed once, as `isKeyedLocation`, rather than as scattered
`=== "metadata"` checks through the form. The same split drives `aggregate`:
keyed locations get `"first"`, because they are recruitment-time constants —
you attribute someone to the ad and metadata they arrived with. Only `variable`
gets `"last"`, since a survey answer is the only one that can meaningfully be
updated later.

**Both text fields change meaning under a lookup**, and the form's prompts say
so, because getting them backwards is the easy mistake:

| Field | Raw read | Ad lookup |
|---|---|---|
| `key` | the metadata key holding the value | the metadata key holding the **token** — usually `vt` |
| `name` | what to call the variable | the **stratum variable** to pull (`creative`, `gender`, `Age`), which is also what it is called |

`applyChange` resets `mapping` to raw when the location moves away from
metadata. Without that a conf could end up `variable` + `ad_table_lookup`, which
is rejected at config time — and worse, its `key` would be read by swoosh as a
declaration of where the token lives, misclassifying every respondent in the
study.

The fly and Qualtrics/Typeform modules are deliberately separate and must stay
that way. Now that `location: "ad"` is gone their *location* lists are
identical; what is fly-only is the **mapping**. A lookup joins on the ad token
and only the fly connector carries one, so offering it on a Qualtrics or
Typeform source would let a user configure a variable that silently yields
nothing forever. `qualtricsExtraction.ts` exports an empty `mappingOptions` —
exported precisely so `flyExtraction.test.ts` can assert the absence rather than
the module merely not mentioning it, which is what stops a future merge of the
two forms from reintroducing it.

`generateLookupConfs.ts` is the third pure module here. It turns the study's
declared variables into `ad_table_lookup` confs, behind an explicit button on
fly sources — mirroring the Strata step's Regenerate. It is additive by name
(a hand-written conf for a variable always wins), emits one token key across
every conf it produces, and is idempotent, so the button is safe to press and
disabled when it would add nothing.

See `documentation/ad-attributions.md` for the join this feeds.

Tests:
`src/pages/StudyConfPage/forms/inferenceData/{flyExtraction,generateLookupConfs}.test.ts`,
run with `npm test`.

## Destination forms and the ref mode

`src/pages/StudyConfPage/forms/destinations/refMode.ts` is the pure module
behind `RefModeField.tsx`, which the Messenger, WhatsApp and multi forms all
render — one control rather than three copies, because the whole point of the
encoded default is that a multi-channel study attributes exactly one way.

Two modes are offered, labelled by consequence rather than mechanism (the word
`ref_mode` never appears on screen): a clean link whose stratum is looked up
afterwards (`encoded`, the default everywhere), and stratum values inline in the
link (`metadata`, Messenger-only). Thin (`shortcode`) is not offered at all.
`isPureMessengerStudy` judges the inline option across the whole destination
list, not per destination, so the Messenger arm of a WhatsApp study cannot take
it.

**The one rule to preserve when editing these forms:** the encoded default is a
*new-conf* affordance and must never be written onto a conf that arrived without
one. `ref_mode` absent is a real, meaningful state — it means the conf predates
the field, and adopt resolves it per channel from `include_metadata_in_ref`. So
`displayedRefMode` reports what a conf actually does and is never written back;
the default lives only in the `emptyStates` in `Destination.tsx` and the
`initialState` in `Destinations.tsx`; and the forms spread `...data` so an
absent field survives an unrelated edit. Break any of the three and editing a
legacy study's welcome message silently flips its ads.
`Messenger.test.tsx` exercises exactly that.

## The Ad Attributions step

`forms/adAttributions/AdAttributions.tsx` shows what each of a study's ads means
and the `ref_token` it carries — a confirmation surface, not a configuration
one. Columns come from adopt rather than being derived here, so the table cannot
show a shape the CSV download beside it does not have. The download is a
fetch-and-object-URL rather than a link, because the endpoint is
bearer-authenticated and an `<a href>` cannot carry the header.

Note that `confs` in `shared.ts` doubles as the wizard's next-step chain
(`getNextConf`), so inserting a step changes where the preceding one advances
to.
