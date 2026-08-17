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

An extraction conf's `location` says where to find one variable's value. A
fly source offers three: `variable` (walk a path into the respondent's
response payload), `metadata` (look up a key in the metadata fly stamped on
the event), and `ad` (look up a key in the frozen `ad_attributions` row for
the ad that recruited the respondent). `metadata` and `ad` are both *keyed*
lookups — you name a key and get a value — while `variable` is the only one
with a response path to select. That distinction is expressed once, as
`isKeyedLocation`, rather than as scattered `=== "metadata"` checks through
the form.

The same split drives `aggregate`: keyed locations (`metadata`, `ad`) get
`"first"`, because they're recruitment-time constants — you attribute someone
to the ad and metadata they arrived with. Only `variable` gets `"last"`,
since a survey answer is the only one of the three that can meaningfully be
updated later.

The fly and Qualtrics/Typeform location lists (`flyExtraction.ts`'s
`locationOptions` vs. `qualtricsExtraction.ts`'s) are deliberately separate
and must stay that way. Only the fly connector populates an event's ad id, so
offering `ad` on a Qualtrics or Typeform source would let a user configure a
variable that silently yields nothing forever. `flyExtraction.test.ts` has a
test asserting `ad` is absent from the Qualtrics list specifically to stop a
future merge of the two forms from reintroducing it.

Tests:
`src/pages/StudyConfPage/forms/inferenceData/flyExtraction.test.ts`, run with
`npm test`.
