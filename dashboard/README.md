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
that module's helpers to `Select`/`TextInput` fields. `extraction.ts` is the
pure module and `Extraction.tsx` the component that consumes it — one of each,
serving fly, Qualtrics and Typeform alike.

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
| `key` | the key or field holding the value | the key or field holding the **token** — `vt` on fly |
| `name` | what to call the variable | the **stratum variable** to pull (`creative`, `gender`, `Age`), which is also what it is called |

`applyChange` leaves `mapping` alone when the location changes. It used to reset
it to raw, because `variable` + `ad_table_lookup` was invalid; that combination
is now how a web or app destination is read back — its respondent lands on the
researcher's own page, so the token returns as a survey field rather than as
fly-stamped event metadata.

**Location and mapping are independent, and so is the form from the source.**
There were two modules, and the only difference was that Qualtrics/Typeform
exported an empty `mappingOptions` so a lookup could not be declared there.
Which data carries a token is a property of the platform, not something a form
can know, so both the split and the second module are gone.

`generateLookupConfs.ts` is the other pure module here. It supplies what a
source starts with when nothing is saved for it: for a fly source, one
`ad_table_lookup` conf per variable declared in Variables, instead of the single
blank row. Purely a default, consumed by `InferenceData.tsx` where it already
builds `initialState` — a source with saved confs shows those, a source without
shows these, and nothing merges the two. Fly only, because the default has to
guess the token's key and `vt` is right only there; not a claim about which
source can carry one.

See `documentation/ad-attributions.md` for the join this feeds.

Tests:
`src/pages/StudyConfPage/forms/inferenceData/{extraction,generateLookupConfs}.test.ts`,
run with `npm test`.

## Destination forms and the ref mode

`src/pages/StudyConfPage/forms/destinations/refMode.ts` is the pure module
behind `RefModeField.tsx`, which every destination form renders — one control
rather than a copy each, because the whole point of the encoded default is that
a multi-channel study attributes exactly one way.

Two modes are offered, labelled by consequence rather than mechanism (the word
`ref_mode` never appears on screen): a clean link whose stratum is looked up
afterwards (`encoded`, the default), and stratum values inline in the link
(`metadata`). There is no third: a ref either carries the stratum or carries a
token that resolves to it, and "carry neither" attributes nobody.

`refModeOptions` takes no arguments, and the signature is the point. It used to
take the study's whole destination list so that the inline option could be
withheld from anything but a pure-Messenger study — a form reasoning about other
destinations to decide what one destination may do. What a ref carries is a
property of the ref; the channel does not remove a mode, and whether anything
reads the token back is configured independently in Data Extraction.

**The one rule to preserve when editing these forms:** the encoded default is a
*new-conf* affordance and must never be written onto a conf that arrived without
one. `ref_mode` absent is a real, meaningful state — it means the conf predates
the field, and adopt resolves it to the inline ref on every channel. So
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
