/**
 * Conformance fixture generator for the Python port of the study-authoring modules.
 *
 * `adopt/adopt/authoring/{strata,extract}.py` are ports of
 * `src/pages/StudyConfPage/forms/strata/strata.ts` and
 * `src/pages/StudyConfPage/forms/variables/extract.ts`. A port is only
 * trustworthy if the two implementations have been run against the same inputs
 * and produced the same outputs, so this program runs the *real* TypeScript
 * over a large, varied case set and prints one JSON document of
 * (name, fn, args, result | error) records. `test_conformance.py` replays every
 * record through the Python and asserts identical output. Same discipline as
 * the slugify differential test (`adopt/adopt/server/slugify.py`).
 *
 * Run:
 *   cd dashboard && npm ci && npx --yes tsx scripts/authoring-conformance.ts
 * or, from adopt/:
 *   make authoring-fixtures
 *
 * Output goes to stdout (pure JSON); a summary goes to stderr.
 *
 * Design notes
 * ------------
 * - Every case's args are canonicalised through JSON *before* being passed to
 *   the function under test, so what the fixture records is exactly what the
 *   TypeScript ran on. There is no `undefined` anywhere in the fixture: both
 *   modules treat `null` and `undefined` identically at every optional
 *   parameter (`!variables.length`, `if (!finishQuestionRef)`, `creatives ? …`,
 *   `!existingStrata`, `if (!adset)`, `!obj || typeof obj !== 'object'`,
 *   `current || []`), so `null` stands in for both and Python's single `None`
 *   maps onto it cleanly.
 * - `fn` is the *Python* name of the function (snake_case). The mapping to the
 *   TypeScript export lives in FNS below, in one place.
 * - Args and results are recorded in the TypeScript's own spelling; the Python
 *   test does the (deliberately tiny) translation. Three names differ, and
 *   only three: the recorded errors carry `adsetName`/`propertyKey` where the
 *   port has `adset_name`/`property_key`, `diffPropertyKeys` returns
 *   `keysDiffer` where the port returns `keys_differ`, and
 *   `formatGroupProduct`'s intermediate levels carry `variableName` where the
 *   port reads `variable_name`. Nothing else may differ.
 *
 * Deliberately excluded — inputs whose TypeScript behaviour is a TypeError (or
 * an unrepresentable value), so they are not conformance targets and would only
 * force the port to emulate a crash:
 * - `formatGroupProduct([], ref)` — `metadata`'s `reduce` has no initial value,
 *   so an empty level list throws. (`createStrataFromVariables` never reaches
 *   it with an empty list: a variable with zero levels short-circuits the
 *   cartesian product to `[]`, which *is* covered.)
 * - `getFinishQuestionRef`/`strataStalenessHint` over saved strata whose first
 *   stratum has no `question_targeting`, or whose `question_targeting.vars` has
 *   no `answered` term: `finishFilter.vars[0]` throws on undefined.
 * - `extractFromAdset(adset, props)` where `adset.targeting` is missing and
 *   `props` is non-empty: `property in undefined` throws.
 * - Levels with no `quota`: the quota reduce yields NaN, which JSON cannot
 *   represent (`JSON.stringify(NaN)` is `null`), so the fixture could not
 *   record the real result. Similarly, saved strata with no `quota` make the
 *   staleness comparison `NaN > 1e-9` → false, which the Python port could only
 *   match by special-casing arithmetic on None.
 * - Existing strata missing `creatives`/`audiences`/`excluded_audiences`: the
 *   merge copies `undefined` into those keys and JSON.stringify then drops
 *   them, so the fixture could not record what the TypeScript actually returned.
 * - Arrays (and other non-plain objects) passed where a targeting blob is
 *   expected, to `isLevelInSync`/`diffPropertyKeys`: `typeof [] === 'object'`,
 *   so JavaScript spreads/enumerates them into `{0: …, 1: …}` index keys.
 *   Matching that would mean writing JS array semantics into the Python port
 *   for an input a targeting blob can never hold. Strings and numbers in the
 *   same position *are* covered — both runtimes treat them as "not an object".
 */
import {
  formatGroupProduct,
  createStrataFromVariables,
  strataStalenessHint,
  getFinishQuestionRef,
} from '../src/pages/StudyConfPage/forms/strata/strata';
import {
  extractFromAdset,
  isLevelInSync,
  diffPropertyKeys,
  AdsetNotFoundError,
  PropertyMissingError,
} from '../src/pages/StudyConfPage/forms/variables/extract';

const SEED = 20260904;

// Python name -> the real TypeScript export. Args arrive as a positional array.
const FNS: Record<string, (...args: any[]) => any> = {
  format_group_product: (levels: any, ref: any) => formatGroupProduct(levels, ref),
  create_strata_from_variables: (v: any, ref: any, cr: any, au: any, ex: any) =>
    createStrataFromVariables(v, ref, cr, au, ex),
  strata_staleness_hint: (v: any, saved: any) => strataStalenessHint(v, saved),
  get_finish_question_ref: (strata: any) => getFinishQuestionRef(strata),
  extract_from_adset: (adset: any, properties: any) => extractFromAdset(adset, properties),
  is_level_in_sync: (stored: any, wouldApply: any) => isLevelInSync(stored, wouldApply),
  diff_property_keys: (stored: any, current: any) => diffPropertyKeys(stored, current),
};

type Case =
  | { name: string; fn: string; args: any[]; result: any }
  | { name: string; fn: string; args: any[]; error: Record<string, any> };

const strataCases: Case[] = [];
const extractCases: Case[] = [];
const seen = new Set<string>();

const copy = <T,>(x: T): T => JSON.parse(JSON.stringify(x === undefined ? null : x));

function runCase(name: string, fn: string, rawArgs: any[]): Case {
  if (seen.has(name)) throw new Error(`duplicate case name: ${name}`);
  seen.add(name);
  if (!FNS[fn]) throw new Error(`unknown fn: ${fn}`);

  // Canonicalise first: the fixture must record exactly what was run.
  const args: any[] = JSON.parse(JSON.stringify(rawArgs.map(a => (a === undefined ? null : a))));

  try {
    const result = FNS[fn](...args);
    return { name, fn, args, result: copy(result) };
  } catch (err: any) {
    if (err instanceof PropertyMissingError) {
      return {
        name,
        fn,
        args,
        error: { name: err.name, adsetName: err.adsetName, propertyKey: err.propertyKey },
      };
    }
    if (err instanceof AdsetNotFoundError) {
      return { name, fn, args, error: { name: err.name, adsetName: err.adsetName } };
    }
    // Anything else is a case we should not be generating — see the exclusion
    // list at the top of this file.
    throw new Error(`case "${name}" threw an unexpected ${err?.name}: ${err?.message}`);
  }
}

const strata = (name: string, fn: string, args: any[]) => strataCases.push(runCase(name, fn, args));
const extract = (name: string, fn: string, args: any[]) => extractCases.push(runCase(name, fn, args));

// ---------------------------------------------------------------------------
// 1. Literal inputs translated verbatim from strata.spec.ts
// ---------------------------------------------------------------------------

const genderLevels = [
  { name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { genders: [1] }, quota: 0.5 },
  { name: 'women', template_campaign: 'foo', template_adset: 'women', facebook_targeting: { genders: [2] }, quota: 0.5 },
];
const genderVariable = { name: 'gender', properties: ['genders'], levels: genderLevels };
const ageVariable = {
  name: 'age',
  properties: ['age_min', 'age_max'],
  levels: [
    { name: '18', template_campaign: 'foo', template_adset: '18-34', facebook_targeting: { age_min: 18, age_max: 34 }, quota: 0.5 },
    { name: '35', template_campaign: 'foo', template_adset: '35-65', facebook_targeting: { age_min: 35, age_max: 65 }, quota: 0.5 },
  ],
};
const locationVariable = {
  name: 'location',
  properties: ['geo_location'],
  levels: [
    { name: 'foo', template_campaign: 'foo', template_adset: 'foo', facebook_targeting: { geo_location: { city: 'foo' } }, quota: 0.5 },
    { name: 'bar', template_campaign: 'foo', template_adset: 'bar', facebook_targeting: { geo_location: { city: 'bar' } }, quota: 0.5 },
    { name: 'baz', template_campaign: 'foo', template_adset: 'baz', facebook_targeting: { geo_location: { city: 'baz' } }, quota: 0.5 },
  ],
};

// 'Empty variables create empty strata' — the spec passes `creatives`
// (undefined) as the second positional arg, i.e. as finishQuestionRef.
strata('spec/empty-variables', 'create_strata_from_variables', [[], null, null, null, null]);

strata('spec/one-variable-multiple-levels', 'create_strata_from_variables', [
  [genderVariable], 'foo', [], null, null,
]);

strata('spec/one-variable-one-level', 'create_strata_from_variables', [
  [{ name: 'gender', properties: ['genders'], levels: [{ name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { genders: [1] }, quota: 1.0 }] }],
  'foo', [], null, null,
]);

strata('spec/two-variables-product', 'create_strata_from_variables', [
  [genderVariable, ageVariable], 'foo', null, null, null,
]);

strata('spec/three-variables-product', 'create_strata_from_variables', [
  [genderVariable, ageVariable, locationVariable], 'foo', null, null, null,
]);

strata('spec/get-finish-ref-empty', 'get_finish_question_ref', [[]]);

const menStratum = {
  audiences: [],
  excluded_audiences: [],
  metadata: { gender: 'men' },
  creatives: [],
  facebook_targeting: { genders: [1] },
  question_targeting: {
    op: 'and',
    vars: [
      { op: 'equal', vars: [{ type: 'variable', value: 'gender' }, { type: 'constant', value: 'men' }] },
      { op: 'answered', vars: [{ type: 'variable', value: 'foo' }] },
    ],
  },
  quota: 0.5,
  id: 'gender:men',
};
strata('spec/get-finish-ref-basic', 'get_finish_question_ref', [[menStratum]]);

strata('spec/merge-preserves-audiences-recomputes-quota', 'create_strata_from_variables', [
  [genderVariable], 'foo', null, null,
  [{
    id: 'gender:men', quota: 0.3, creatives: ['creative_A'], audiences: ['audience_1'],
    excluded_audiences: ['excluded_1'], facebook_targeting: { genders: [1] }, metadata: { gender: 'men' },
  }],
]);

strata('spec/merge-drops-missing-ids', 'create_strata_from_variables', [
  [{ name: 'gender', properties: ['genders'], levels: [genderLevels[0]] }], 'foo', null, null,
  [
    { id: 'gender:men', quota: 0.5, creatives: ['creative_A'], audiences: [], excluded_audiences: [], facebook_targeting: { genders: [1] }, metadata: { gender: 'men' } },
    { id: 'gender:women', quota: 0.5, creatives: ['creative_A'], audiences: [], excluded_audiences: [], facebook_targeting: { genders: [2] }, metadata: { gender: 'women' } },
  ],
]);

strata('spec/merge-adds-new-combinations', 'create_strata_from_variables', [
  [genderVariable], 'foo', null, null,
  [{ id: 'gender:men', quota: 0.5, creatives: ['creative_A'], audiences: ['audience_1'], excluded_audiences: [], facebook_targeting: { genders: [1] }, metadata: { gender: 'men' } }],
]);

const qt = (variableName: string, level: string, ref: string) => ({
  op: 'and',
  vars: [
    { op: 'equal', vars: [{ type: 'variable', value: variableName }, { type: 'constant', value: level }] },
    { op: 'answered', vars: [{ type: 'variable', value: ref }] },
  ],
});

const savedMenOnly = [{
  id: 'gender:men', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
  facebook_targeting: { genders: [1] }, question_targeting: qt('gender', 'men', 'finish_q'),
  metadata: { gender: 'men' },
}];

strata('spec/staleness-level-added', 'strata_staleness_hint', [[genderVariable], savedMenOnly]);

strata('spec/staleness-nothing-changed', 'strata_staleness_hint', [
  [{ name: 'gender', properties: ['genders'], levels: [genderLevels[0]] }], savedMenOnly,
]);

const ageOneLevel = {
  name: 'age',
  properties: ['age_min', 'age_max'],
  levels: [{ name: '18-34', template_campaign: 'foo', template_adset: '18-34', facebook_targeting: { age_min: 18, age_max: 34 }, quota: 0.5 }],
};

strata('spec/staleness-targeting-key-order', 'strata_staleness_hint', [
  [ageOneLevel],
  [{
    id: 'age:18-34', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_max: 34, age_min: 18 }, question_targeting: qt('age', '18-34', 'finish_q'),
    metadata: { age: '18-34' },
  }],
]);

strata('spec/staleness-targeting-values-differ', 'strata_staleness_hint', [
  [ageOneLevel],
  [{
    id: 'age:18-34', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 25, age_max: 34 }, question_targeting: qt('age', '18-34', 'finish_q'),
    metadata: { age: '18-34' },
  }],
]);

// 'Regenerate propagates changed level quotas from Variables'
const genderVariables = (menQuota: number, womenQuota: number) => ([{
  name: 'gender',
  properties: ['genders'],
  levels: [
    { name: 'men', template_campaign: 'foo', template_adset: 'men', facebook_targeting: { genders: [1] }, quota: menQuota },
    { name: 'women', template_campaign: 'foo', template_adset: 'women', facebook_targeting: { genders: [2] }, quota: womenQuota },
  ],
}]);

const regenSaved = [
  { id: 'gender:men', quota: 0.5, creatives: ['creative_A'], audiences: [], excluded_audiences: [], facebook_targeting: { genders: [1] }, metadata: { gender: 'men' }, question_targeting: qt('gender', 'men', 'foo') },
  { id: 'gender:women', quota: 0.5, creatives: ['creative_A'], audiences: [], excluded_audiences: [], facebook_targeting: { genders: [2] }, metadata: { gender: 'women' }, question_targeting: qt('gender', 'women', 'foo') },
];

strata('spec/regen-recomputes-quotas', 'create_strata_from_variables', [
  genderVariables(0.7, 0.3), 'foo', null, null, regenSaved,
]);
strata('spec/regen-preserves-creatives', 'create_strata_from_variables', [
  genderVariables(0.7, 0.3), 'foo', [{ name: 'creative_B' }], null, regenSaved,
]);
strata('spec/regen-staleness-quotas-changed', 'strata_staleness_hint', [genderVariables(0.7, 0.3), regenSaved]);
strata('spec/regen-staleness-quotas-same', 'strata_staleness_hint', [genderVariables(0.5, 0.5), regenSaved]);

// ---------------------------------------------------------------------------
// 2. Hand-written strata edge cases
// ---------------------------------------------------------------------------

const lvl = (name: string, targeting: any, quota: number) => ({
  name, template_campaign: 'tc', template_adset: `adset-${name}`, facebook_targeting: targeting, quota,
});
const vbl = (name: string, levels: any[], properties: string[] = []) => ({ name, properties, levels });

strata('edge/single-variable-single-level', 'create_strata_from_variables', [
  [vbl('gender', [lvl('men', { genders: [1] }, 1)])], 'q1', null, null, null,
]);

strata('edge/one-variable-zero-levels', 'create_strata_from_variables', [
  [vbl('gender', [])], 'q1', null, null, null,
]);

strata('edge/two-variables-one-with-zero-levels', 'create_strata_from_variables', [
  [genderVariable, vbl('age', [])], 'q1', null, null, null,
]);

strata('edge/zero-levels-first-variable', 'create_strata_from_variables', [
  [vbl('age', []), genderVariable], 'q1', null, null, null,
]);

strata('edge/three-variables', 'create_strata_from_variables', [
  [
    vbl('gender', [lvl('m', { genders: [1] }, 0.5), lvl('f', { genders: [2] }, 0.5)]),
    vbl('age', [lvl('young', { age_min: 18, age_max: 24 }, 0.4), lvl('old', { age_min: 25, age_max: 65 }, 0.6)]),
    vbl('loc', [lvl('north', { geo_locations: { regions: [{ key: '1' }] } }, 0.25)]),
  ], 'q1', ['c1', 'c2'].map(n => ({ name: n })), [{ name: 'a1', subtype: 'CUSTOM' }], null,
]);

strata('edge/four-variables', 'create_strata_from_variables', [
  [
    vbl('gender', [lvl('m', { genders: [1] }, 0.5), lvl('f', { genders: [2] }, 0.5)]),
    vbl('age', [lvl('y', { age_min: 18 }, 0.5), lvl('o', { age_min: 45 }, 0.5)]),
    vbl('loc', [lvl('n', { geo_locations: { countries: ['NG'] } }, 0.5), lvl('s', { geo_locations: { countries: ['KE'] } }, 0.5)]),
    vbl('lang', [lvl('en', { locales: [6] }, 0.5), lvl('sw', { locales: [24] }, 0.5)]),
  ], 'q1', null, null, null,
]);

// Duplicate targeting keys across levels: the reduce is a shallow merge, so the
// LAST variable's value wins. Exercises the overwrite order explicitly.
strata('edge/duplicate-targeting-keys-two-way', 'create_strata_from_variables', [
  [
    vbl('a', [lvl('a1', { age_min: 18, age_max: 24, genders: [1] }, 0.5)]),
    vbl('b', [lvl('b1', { age_min: 30, locales: [6] }, 0.5)]),
  ], 'q1', null, null, null,
]);

strata('edge/duplicate-targeting-keys-three-way', 'create_strata_from_variables', [
  [
    vbl('a', [lvl('a1', { k: 'first', shared: 1 }, 1)]),
    vbl('b', [lvl('b1', { k: 'second', other: 2 }, 1)]),
    vbl('c', [lvl('c1', { k: 'third', shared: 3 }, 1)]),
  ], 'q1', null, null, null,
]);

// The merge is shallow, so a whole nested object is replaced, not deep-merged.
strata('edge/nested-targeting-shallow-overwrite', 'create_strata_from_variables', [
  [
    vbl('a', [lvl('a1', { geo_locations: { countries: ['NG'], location_types: ['home'] } }, 1)]),
    vbl('b', [lvl('b1', { geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi', radius: 25 }] } }, 1)]),
  ], 'q1', null, null, null,
]);

strata('edge/deeply-nested-targeting', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', {
    flexible_spec: [{ interests: [{ id: '6003', name: 'Health' }], behaviors: [] }],
    geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi', radius: 25, distance_unit: 'kilometer' }], location_types: ['home', 'recent'] },
    excluded_geo_locations: { regions: [{ key: '3868', name: 'Lagos' }] },
  }, 1)])], 'q1', null, null, null,
]);

strata('edge/empty-targeting-object', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', {}, 0.5), lvl('a2', {}, 0.5)])], 'q1', null, null, null,
]);

// A saved conf can carry a level with no usable targeting — Variables.tsx
// guards on `!level.facebook_targeting`. `{...null}` and `{...undefined}` are
// both `{}` in JS.
strata('edge/null-targeting', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', null, 0.5)])], 'q1', null, null, null,
]);
strata('edge/absent-targeting-key', 'create_strata_from_variables', [
  [{ name: 'a', properties: [], levels: [{ name: 'a1', template_campaign: 'tc', template_adset: 'x', quota: 0.5 }] }],
  'q1', null, null, null,
]);
strata('edge/null-targeting-mixed-with-real', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', null, 0.5)]), vbl('b', [lvl('b1', { age_min: 18 }, 0.5)])], 'q1', null, null, null,
]);

strata('edge/level-name-with-separators', 'create_strata_from_variables', [
  [vbl('a', [lvl('x,y', { age_min: 18 }, 0.5), lvl('p:q', { age_min: 25 }, 0.5)])], 'q1', null, null, null,
]);
strata('edge/level-name-empty-string', 'create_strata_from_variables', [
  [vbl('a', [lvl('', { age_min: 18 }, 1)])], 'q1', null, null, null,
]);
strata('edge/variable-name-unicode', 'create_strata_from_variables', [
  [vbl('genré', [lvl('femmesé', { genders: [2] }, 1)])], 'q1', null, null, null,
]);

// Duplicate variable names: metadata collapses to one key, question_targeting
// keeps both terms, and the id keeps both segments.
strata('edge/duplicate-variable-names', 'create_strata_from_variables', [
  [vbl('gender', [lvl('m', { genders: [1] }, 0.5)]), vbl('gender', [lvl('f', { genders: [2] }, 0.5)])],
  'q1', null, null, null,
]);

strata('edge/quota-zero', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 0), lvl('a2', { age_min: 25 }, 1)])], 'q1', null, null, null,
]);
strata('edge/quota-integers', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 3)]), vbl('b', [lvl('b1', { age_max: 65 }, 4)])], 'q1', null, null, null,
]);
// 0.1 * 0.3 * 0.7 in IEEE double, computed left to right by both runtimes.
strata('edge/quota-float-product', 'create_strata_from_variables', [
  [
    vbl('a', [lvl('a1', { age_min: 18 }, 0.1)]),
    vbl('b', [lvl('b1', { age_max: 65 }, 0.3)]),
    vbl('c', [lvl('c1', { genders: [1] }, 0.7)]),
  ], 'q1', null, null, null,
]);
strata('edge/quota-float-product-repeating', 'create_strata_from_variables', [
  [
    vbl('a', [lvl('a1', {}, 0.3333333333333333)]),
    vbl('b', [lvl('b1', {}, 0.6666666666666666)]),
    vbl('c', [lvl('c1', {}, 1e-7)]),
  ], 'q1', null, null, null,
]);
strata('edge/quota-large-and-small', 'create_strata_from_variables', [
  [vbl('a', [lvl('a1', {}, 1e12)]), vbl('b', [lvl('b1', {}, 1e-12)])], 'q1', null, null, null,
]);

strata('edge/no-finish-question-ref', 'create_strata_from_variables', [
  [genderVariable], null, [{ name: 'c1' }], null, null,
]);
strata('edge/finish-question-ref-empty-string', 'create_strata_from_variables', [
  [genderVariable], '', null, null, null,
]);
strata('edge/creatives-and-audiences', 'create_strata_from_variables', [
  [genderVariable], 'q1',
  [{ name: 'c1' }, { name: 'c2' }, { name: 'c3' }],
  [{ name: 'a1', subtype: 'CUSTOM' }, { name: 'a2', subtype: 'LOOKALIKE' }],
  null,
]);
strata('edge/empty-creatives-and-audiences-lists', 'create_strata_from_variables', [
  [genderVariable], 'q1', [], [], null,
]);

// existing_strata merges
const freshGender = createStrataFromVariables([genderVariable] as any, 'q1');
strata('edge/existing-strata-empty-list', 'create_strata_from_variables', [
  [genderVariable], 'q1', null, null, [],
]);
strata('edge/existing-strata-full-overlap', 'create_strata_from_variables', [
  [genderVariable], 'q1', [{ name: 'fresh_c' }], [{ name: 'fresh_a' }], copy(freshGender).map((s: any, i: number) => ({
    ...s, quota: 0.99, creatives: [`old_c${i}`], audiences: [`old_a${i}`], excluded_audiences: [`old_x${i}`],
    facebook_targeting: { stale: true },
  })),
]);
strata('edge/existing-strata-partial-overlap', 'create_strata_from_variables', [
  [genderVariable], 'q1', null, null,
  [
    { id: 'gender:men', quota: 0.1, creatives: ['kept_c'], audiences: ['kept_a'], excluded_audiences: ['kept_x'], facebook_targeting: { genders: [9] }, metadata: { gender: 'stale' } },
    { id: 'gender:nonbinary', quota: 0.4, creatives: ['dropped'], audiences: [], excluded_audiences: [], facebook_targeting: {}, metadata: {} },
  ],
]);
strata('edge/existing-strata-no-overlap', 'create_strata_from_variables', [
  [genderVariable], 'q1', [{ name: 'c1' }], null,
  [{ id: 'age:18', quota: 0.4, creatives: ['x'], audiences: ['y'], excluded_audiences: ['z'], facebook_targeting: {}, metadata: {} }],
]);
strata('edge/existing-strata-duplicate-ids-last-wins', 'create_strata_from_variables', [
  [genderVariable], 'q1', null, null,
  [
    { id: 'gender:men', quota: 0.1, creatives: ['first'], audiences: ['first_a'], excluded_audiences: [], facebook_targeting: {}, metadata: {} },
    { id: 'gender:men', quota: 0.2, creatives: ['second'], audiences: ['second_a'], excluded_audiences: ['second_x'], facebook_targeting: {}, metadata: {} },
  ],
]);
strata('edge/existing-strata-extra-keys-ignored', 'create_strata_from_variables', [
  [genderVariable], 'q1', null, null,
  [{ id: 'gender:men', quota: 0.1, creatives: [], audiences: [], excluded_audiences: [], facebook_targeting: {}, metadata: {}, some_unknown_field: { a: 1 } }],
]);
strata('edge/existing-strata-empty-string-lists', 'create_strata_from_variables', [
  [genderVariable], 'q1', [{ name: 'c1' }], [{ name: 'a1' }],
  [{ id: 'gender:women', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [], facebook_targeting: {}, metadata: {} }],
]);

// staleness
strata('edge/staleness-no-saved-strata', 'strata_staleness_hint', [[genderVariable], null]);
strata('edge/staleness-no-saved-strata-no-variables', 'strata_staleness_hint', [[], null]);
strata('edge/staleness-empty-saved-list', 'strata_staleness_hint', [[genderVariable], []]);
strata('edge/staleness-empty-saved-list-no-variables', 'strata_staleness_hint', [[], []]);
strata('edge/staleness-saved-longer-than-fresh', 'strata_staleness_hint', [
  [{ name: 'gender', properties: [], levels: [genderLevels[0]] }],
  [savedMenOnly[0], { ...savedMenOnly[0], id: 'gender:women', facebook_targeting: { genders: [2] } }],
]);
strata('edge/staleness-different-ids-same-length', 'strata_staleness_hint', [
  [{ name: 'gender', properties: [], levels: [genderLevels[0]] }],
  [{ ...savedMenOnly[0], id: 'gender:nonbinary' }],
]);
strata('edge/staleness-reordered-nested-keys', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { geo_locations: { countries: ['NG'], location_types: ['home'] }, age_min: 18 }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 18, geo_locations: { location_types: ['home'], countries: ['NG'] } },
    question_targeting: qt('a', 'a1', 'q1'), metadata: { a: 'a1' },
  }],
]);
strata('edge/staleness-reordered-array-values', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { genders: [1, 2] }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { genders: [2, 1] }, question_targeting: qt('a', 'a1', 'q1'), metadata: {},
  }],
]);
strata('edge/staleness-quota-within-tolerance', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5 + 1e-12, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 18 }, question_targeting: qt('a', 'a1', 'q1'), metadata: {},
  }],
]);
strata('edge/staleness-quota-outside-tolerance', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5 + 1e-8, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 18 }, question_targeting: qt('a', 'a1', 'q1'), metadata: {},
  }],
]);
strata('edge/staleness-targeting-added-key', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 18, age_max: 65 }, question_targeting: qt('a', 'a1', 'q1'), metadata: {},
  }],
]);
strata('edge/staleness-saved-targeting-empty', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', {}, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: {}, question_targeting: qt('a', 'a1', 'q1'), metadata: {},
  }],
]);
strata('edge/staleness-variables-empty-saved-present', 'strata_staleness_hint', [[], savedMenOnly]);
strata('edge/staleness-answered-ref-not-last-term', 'strata_staleness_hint', [
  [vbl('a', [lvl('a1', { age_min: 18 }, 0.5)])],
  [{
    id: 'a:a1', quota: 0.5, creatives: [], audiences: [], excluded_audiences: [],
    facebook_targeting: { age_min: 18 },
    question_targeting: {
      op: 'and',
      vars: [
        { op: 'answered', vars: [{ type: 'variable', value: 'finish_first' }] },
        { op: 'equal', vars: [{ type: 'variable', value: 'a' }, { type: 'constant', value: 'a1' }] },
      ],
    },
    metadata: {},
  }],
]);

// format_group_product directly
strata('edge/format-group-product-single-level', 'format_group_product', [
  [{ ...lvl('men', { genders: [1] }, 0.5), variableName: 'gender' }], 'q1',
]);
strata('edge/format-group-product-three-levels-overwrite', 'format_group_product', [
  [
    { ...lvl('a1', { age_min: 18, shared: 'first' }, 0.5), variableName: 'a' },
    { ...lvl('b1', { age_max: 65, shared: 'second' }, 0.4), variableName: 'b' },
    { ...lvl('c1', { shared: 'third', genders: [2] }, 0.25), variableName: 'c' },
  ], 'finish',
]);
strata('edge/format-group-product-null-targeting', 'format_group_product', [
  [{ ...lvl('a1', null, 1), variableName: 'a' }], 'finish',
]);
strata('edge/format-group-product-empty-ref', 'format_group_product', [
  [{ ...lvl('a1', { age_min: 18 }, 1), variableName: 'a' }], '',
]);
strata('edge/format-group-product-duplicate-variable-names', 'format_group_product', [
  [
    { ...lvl('m', { genders: [1] }, 0.5), variableName: 'gender' },
    { ...lvl('f', { genders: [2] }, 0.5), variableName: 'gender' },
  ], 'finish',
]);

// get_finish_question_ref
strata('edge/get-finish-ref-answered-first', 'get_finish_question_ref', [[{
  ...menStratum,
  question_targeting: {
    op: 'and',
    vars: [
      { op: 'answered', vars: [{ type: 'variable', value: 'first_answered' }] },
      { op: 'equal', vars: [{ type: 'variable', value: 'gender' }, { type: 'constant', value: 'men' }] },
    ],
  },
}]]);
strata('edge/get-finish-ref-multiple-answered-terms', 'get_finish_question_ref', [[{
  ...menStratum,
  question_targeting: {
    op: 'and',
    vars: [
      { op: 'answered', vars: [{ type: 'variable', value: 'one' }] },
      { op: 'answered', vars: [{ type: 'variable', value: 'two' }] },
    ],
  },
}]]);
strata('edge/get-finish-ref-only-first-stratum-read', 'get_finish_question_ref', [[
  menStratum,
  { ...menStratum, id: 'gender:women', question_targeting: qt('gender', 'women', 'other_ref') },
]]);
strata('edge/get-finish-ref-ref-is-empty-string', 'get_finish_question_ref', [[{
  ...menStratum, question_targeting: qt('gender', 'men', ''),
}]]);

// ---------------------------------------------------------------------------
// 3. Literal inputs translated verbatim from extract.test.ts
// ---------------------------------------------------------------------------

const mockAdset = {
  id: 'adset-123',
  name: 'Test Adset',
  targeting: {
    geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi' }] },
    age_min: 18,
    age_max: 65,
    genders: [1],
    targeting_automation: { advantage_audience: 1, individual_setting: { age: 1, gender: 0, geo: 0 } },
  },
};

extract('spec/extract-requested-properties', 'extract_from_adset', [mockAdset, ['geo_locations', 'age_min', 'age_max']]);
extract('spec/extract-forces-advantage-audience-off', 'extract_from_adset', [mockAdset, ['geo_locations']]);
// The spec sets `targeting_automation: undefined`; JSON cannot hold that, and
// `undefined` and an absent key behave identically here (the key is never read).
extract('spec/extract-source-without-targeting-automation', 'extract_from_adset', [
  { id: mockAdset.id, name: mockAdset.name, targeting: { geo_locations: mockAdset.targeting.geo_locations, age_min: 18, age_max: 65, genders: [1] } },
  ['geo_locations'],
]);
extract('spec/extract-source-already-disabled', 'extract_from_adset', [
  { ...mockAdset, targeting: { ...mockAdset.targeting, targeting_automation: { advantage_audience: 0 } } },
  ['geo_locations'],
]);
extract('spec/extract-null-adset', 'extract_from_adset', [null, ['geo_locations']]);
extract('spec/extract-undefined-adset', 'extract_from_adset', [undefined, ['geo_locations']]);
extract('spec/extract-missing-property-among-others', 'extract_from_adset', [mockAdset, ['geo_locations', 'custom_audiences']]);
extract('spec/extract-missing-property-alone', 'extract_from_adset', [mockAdset, ['custom_audiences']]);
extract('spec/extract-no-requested-properties', 'extract_from_adset', [
  { id: 'adset-456', name: 'Minimal Adset', targeting: { targeting_automation: { advantage_audience: 1, individual_setting: { age: 1 } } } },
  [],
]);

extract('spec/in-sync-identical', 'is_level_in_sync', [
  { age_min: 18, geo_locations: { countries: ['US'] } },
  { age_min: 18, geo_locations: { countries: ['US'] } },
]);
extract('spec/in-sync-top-level-key-order', 'is_level_in_sync', [
  { age_max: 45, age_min: 18, geo_locations: { countries: ['NG'] } },
  { age_min: 18, age_max: 45, geo_locations: { countries: ['NG'] } },
]);
extract('spec/in-sync-nested-key-order', 'is_level_in_sync', [
  { geo_locations: { countries: ['NG'], location_types: ['home'] } },
  { geo_locations: { location_types: ['home'], countries: ['NG'] } },
]);
extract('spec/in-sync-ignores-targeting-automation', 'is_level_in_sync', [
  { age_min: 18 }, { age_min: 18, targeting_automation: { advantage_audience: 0 } },
]);
extract('spec/in-sync-values-differ', 'is_level_in_sync', [{ age_min: 18 }, { age_min: 25 }]);
extract('spec/in-sync-stored-empty', 'is_level_in_sync', [{}, { age_min: 18 }]);
extract('spec/in-sync-both-empty', 'is_level_in_sync', [{}, {}]);
extract('spec/in-sync-both-null', 'is_level_in_sync', [null, null]);
extract('spec/in-sync-both-undefined', 'is_level_in_sync', [undefined, undefined]);
extract('spec/in-sync-null-vs-values', 'is_level_in_sync', [null, { age_min: 18 }]);

extract('spec/diff-keys-match', 'diff_property_keys', [
  { age_min: 18, genders: [1], targeting_automation: { advantage_audience: 0 } }, ['age_min', 'genders'],
]);
extract('spec/diff-keys-added', 'diff_property_keys', [{ age_min: 18 }, ['age_min', 'genders']]);
extract('spec/diff-keys-removed', 'diff_property_keys', [{ age_min: 18, genders: [1] }, ['age_min']]);
extract('spec/diff-keys-empty-current-removes-all', 'diff_property_keys', [{ age_min: 18, genders: [1] }, []]);
extract('spec/diff-keys-ignores-targeting-automation', 'diff_property_keys', [
  { age_min: 18, targeting_automation: { advantage_audience: 0 } }, ['age_min'],
]);
extract('spec/diff-keys-null-stored', 'diff_property_keys', [null, ['age_min']]);
extract('spec/diff-keys-undefined-stored-empty-current', 'diff_property_keys', [undefined, []]);

// ---------------------------------------------------------------------------
// 4. Hand-written extract edge cases
// ---------------------------------------------------------------------------

extract('edge/extract-name-empty-string-falls-back-to-id', 'extract_from_adset', [
  { id: 'adset-777', name: '', targeting: { age_min: 18 } }, ['genders'],
]);
extract('edge/extract-name-absent-falls-back-to-id', 'extract_from_adset', [
  { id: 'adset-778', targeting: { age_min: 18 } }, ['genders'],
]);
extract('edge/extract-name-null-falls-back-to-id', 'extract_from_adset', [
  { id: 'adset-779', name: null, targeting: { age_min: 18 } }, ['genders'],
]);
extract('edge/extract-empty-targeting-empty-properties', 'extract_from_adset', [
  { id: 'adset-780', name: 'Empty', targeting: {} }, [],
]);
extract('edge/extract-empty-targeting-missing-property', 'extract_from_adset', [
  { id: 'adset-781', name: 'Empty', targeting: {} }, ['age_min'],
]);
extract('edge/extract-property-value-null', 'extract_from_adset', [
  { id: 'a', name: 'Null value', targeting: { age_min: null, genders: [1] } }, ['age_min', 'genders'],
]);
extract('edge/extract-property-value-falsy', 'extract_from_adset', [
  { id: 'a', name: 'Falsy values', targeting: { age_min: 0, flag: false, label: '' } }, ['age_min', 'flag', 'label'],
]);
extract('edge/extract-duplicate-properties-requested', 'extract_from_adset', [
  { id: 'a', name: 'Dupes', targeting: { age_min: 18 } }, ['age_min', 'age_min'],
]);
// targeting_automation requested explicitly is extracted and then overwritten
// by the forced value.
extract('edge/extract-targeting-automation-requested', 'extract_from_adset', [
  { id: 'a', name: 'TA', targeting: { targeting_automation: { advantage_audience: 1, individual_setting: { age: 1 } }, age_min: 18 } },
  ['targeting_automation', 'age_min'],
]);
extract('edge/extract-deep-nested-property', 'extract_from_adset', [
  {
    id: 'a', name: 'Deep',
    targeting: {
      flexible_spec: [{ interests: [{ id: '6003139266461', name: 'Health' }] }, { behaviors: [{ id: '1', name: 'b' }] }],
      geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi', radius: 25, distance_unit: 'kilometer' }], location_types: ['home', 'recent'] },
    },
  },
  ['flexible_spec', 'geo_locations'],
]);
extract('edge/extract-missing-property-first-in-list', 'extract_from_adset', [
  { id: 'a', name: 'First missing', targeting: { age_min: 18, genders: [1] } }, ['nope', 'age_min'],
]);
extract('edge/extract-all-targeting-properties', 'extract_from_adset', [
  mockAdset, ['geo_locations', 'age_min', 'age_max', 'genders', 'targeting_automation'],
]);
extract('edge/extract-property-order-reversed', 'extract_from_adset', [
  mockAdset, ['age_max', 'age_min', 'geo_locations'],
]);
extract('edge/extract-null-adset-empty-properties', 'extract_from_adset', [null, []]);

extract('edge/in-sync-both-only-targeting-automation', 'is_level_in_sync', [
  { targeting_automation: { advantage_audience: 0 } }, { targeting_automation: { advantage_audience: 1 } },
]);
extract('edge/in-sync-null-vs-empty-object', 'is_level_in_sync', [null, {}]);
extract('edge/in-sync-array-value-order-differs', 'is_level_in_sync', [
  { genders: [1, 2] }, { genders: [2, 1] },
]);
extract('edge/in-sync-number-vs-string-value', 'is_level_in_sync', [{ age_min: 18 }, { age_min: '18' }]);
extract('edge/in-sync-nested-extra-key', 'is_level_in_sync', [
  { geo_locations: { countries: ['NG'] } }, { geo_locations: { countries: ['NG'], location_types: ['home'] } },
]);
extract('edge/in-sync-deeply-equal', 'is_level_in_sync', [
  { flexible_spec: [{ interests: [{ id: '1', name: 'a' }] }], geo_locations: { cities: [{ key: 'NG-BA', radius: 25 }] } },
  { geo_locations: { cities: [{ radius: 25, key: 'NG-BA' }] }, flexible_spec: [{ interests: [{ name: 'a', id: '1' }] }] },
]);
extract('edge/in-sync-deeply-different', 'is_level_in_sync', [
  { flexible_spec: [{ interests: [{ id: '1', name: 'a' }] }] },
  { flexible_spec: [{ interests: [{ id: '1', name: 'b' }] }] },
]);
extract('edge/in-sync-strings', 'is_level_in_sync', ['a', 'b']);
extract('edge/in-sync-numbers', 'is_level_in_sync', [1, 2]);
extract('edge/in-sync-string-vs-object', 'is_level_in_sync', ['a', { age_min: 18 }]);
extract('edge/in-sync-number-vs-empty-object', 'is_level_in_sync', [0, {}]);
extract('edge/in-sync-null-vs-only-targeting-automation', 'is_level_in_sync', [
  null, { targeting_automation: { advantage_audience: 0 } },
]);
extract('edge/in-sync-nested-null-values', 'is_level_in_sync', [
  { geo_locations: null }, { geo_locations: null },
]);
extract('edge/in-sync-null-vs-missing-key', 'is_level_in_sync', [{ geo_locations: null }, {}]);

extract('edge/diff-keys-both-empty', 'diff_property_keys', [{}, []]);
extract('edge/diff-keys-null-current', 'diff_property_keys', [{ age_min: 18 }, null]);
extract('edge/diff-keys-only-targeting-automation-stored', 'diff_property_keys', [
  { targeting_automation: { advantage_audience: 0 } }, [],
]);
extract('edge/diff-keys-current-order-differs', 'diff_property_keys', [
  { age_min: 18, genders: [1], geo_locations: {} }, ['geo_locations', 'genders', 'age_min'],
]);
extract('edge/diff-keys-duplicates-in-current', 'diff_property_keys', [{ age_min: 18 }, ['age_min', 'age_min']]);
extract('edge/diff-keys-current-includes-targeting-automation', 'diff_property_keys', [
  { age_min: 18, targeting_automation: { advantage_audience: 0 } }, ['age_min', 'targeting_automation'],
]);
extract('edge/diff-keys-both-added-and-removed', 'diff_property_keys', [
  { age_min: 18, genders: [1] }, ['age_min', 'geo_locations', 'locales'],
]);
extract('edge/diff-keys-completely-disjoint', 'diff_property_keys', [
  { a: 1, b: 2 }, ['c', 'd'],
]);
extract('edge/diff-keys-stored-string', 'diff_property_keys', ['not an object', ['age_min']]);
extract('edge/diff-keys-stored-number', 'diff_property_keys', [5, []]);
extract('edge/diff-keys-stored-boolean', 'diff_property_keys', [true, ['age_min']]);
extract('edge/diff-keys-key-sort-order', 'diff_property_keys', [
  { B: 1, a: 2, _z: 3 }, ['a', '_z'],
]);
extract('edge/diff-keys-null-stored-null-current', 'diff_property_keys', [null, null]);

// ---------------------------------------------------------------------------
// 5. Seeded pseudo-random cases
// ---------------------------------------------------------------------------

// mulberry32 — a tiny deterministic PRNG, so regeneration is reproducible and
// the fixture file diffs cleanly. No dependency.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(SEED);
const rint = (lo: number, hi: number) => lo + Math.floor(rand() * (hi - lo + 1));
const pick = <T,>(xs: T[]): T => xs[rint(0, xs.length - 1)];
const chance = (p: number) => rand() < p;
const shuffled = <T,>(xs: T[]): T[] => {
  const out = xs.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = rint(0, i);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
};

// A small vocabulary, so the shallow merge across variables actually collides.
const CORE_KEYS = ['age_min', 'age_max', 'genders', 'geo_locations', 'interests'];
const EXTRA_KEYS = ['locales', 'flexible_spec', 'excluded_geo_locations', 'publisher_platforms', 'device_platforms'];

// Weighted rather than uniform: the nested shapes are the ones that blow up the
// fixture's byte count, so they appear often enough to exercise deep equality
// and the shallow-merge overwrite, and no more often than that.
function randomTargetingValue(): any {
  const r = rand();
  if (r < 0.30) return rint(13, 65);
  if (r < 0.50) return [rint(1, 2)];
  if (r < 0.62) return [pick(['NG', 'KE', 'US', 'IN']), pick(['home', 'recent'])];
  if (r < 0.76) return { countries: [pick(['NG', 'KE'])], location_types: shuffled(['home', 'recent']).slice(0, rint(1, 2)) };
  if (r < 0.82) return { cities: [{ key: `NG-${rint(1, 99)}`, name: pick(['Bauchi', 'Kano', 'Lagos']), radius: rint(1, 50) }] };
  if (r < 0.92) return Math.round(rand() * 1e4) / 1e4;
  return pick([true, false, pick(['mobile', 'desktop']), rint(0, 3)]);
}

function randomTargeting(): any {
  const keys = shuffled(CORE_KEYS).slice(0, rint(0, 3));
  if (chance(0.3)) keys.push(pick(EXTRA_KEYS));
  const out: any = {};
  for (const k of keys) out[k] = randomTargetingValue();
  return out;
}

const randomQuota = () => pick([0.5, 0.25, 1, 0.1, 0.7, 0.3, 0.333, 2, 0, Math.round(rand() * 1000) / 1000]);

const VAR_NAMES = ['gender', 'age', 'location', 'device', 'income', 'language'];

function randomVariables(): any[] {
  const n = rint(1, 4);
  const counts: number[] = [];
  // Level counts run 0..4, but a zero collapses the whole cartesian product to
  // [], which tests only the short-circuit — so draw it sparingly rather than
  // uniformly, and spend the case budget on products that actually have strata.
  for (let i = 0; i < n; i++) counts.push(chance(0.08) ? 0 : rint(1, 4));
  // Cap the cartesian product so the fixture file stays diffable. Level counts
  // stay in 0..4; only the combination count is bounded.
  const product = () => counts.reduce((a, b) => a * b, 1);
  while (product() > 4) {
    const biggest = counts.indexOf(Math.max(...counts));
    counts[biggest] -= 1;
  }
  const names = shuffled(VAR_NAMES).slice(0, n);
  return names.map((name, i) => ({
    name,
    properties: shuffled(CORE_KEYS).slice(0, rint(0, 2)),
    levels: Array.from({ length: counts[i] }, (_, j) => ({
      name: `l${j}`,
      template_campaign: `tc-${name}`,
      template_adset: `ts-${name}-${j}`,
      facebook_targeting: randomTargeting(),
      quota: randomQuota(),
    })),
  }));
}

function mutateVariables(vars: any[]): any[] {
  const out = copy(vars);
  if (!out.length) return out;
  const v = out[rint(0, out.length - 1)];
  switch (rint(0, 3)) {
    case 0:
      if (v.levels.length) v.levels[rint(0, v.levels.length - 1)].quota = randomQuota();
      break;
    case 1:
      v.levels.push({
        name: `l${v.levels.length}`, template_campaign: 'tc', template_adset: 'ts',
        facebook_targeting: randomTargeting(), quota: randomQuota(),
      });
      break;
    case 2:
      if (v.levels.length) v.levels.pop();
      break;
    default:
      if (v.levels.length) v.levels[0].facebook_targeting = { ...v.levels[0].facebook_targeting, age_min: rint(13, 65) };
      break;
  }
  return out;
}

const reorderKeys = (obj: any): any => {
  if (!obj || typeof obj !== 'object') return obj;
  const out: any = {};
  for (const k of Object.keys(obj).reverse()) out[k] = obj[k];
  return out;
};

// A perturbed copy of the fresh strata, standing in for what a study has saved.
// Always keeps creatives/audiences/excluded_audiences present and quota numeric
// (see the exclusion list), and never touches question_targeting, so
// getFinishQuestionRef stays well defined.
function perturbStrata(fresh: any[]): any[] {
  let out: any[] = copy(fresh);
  if (!out.length) return out;
  if (out.length > 1 && chance(0.25)) out = out.slice(0, -1);
  if (chance(0.2)) out[0] = { ...out[0], id: `${out[0].id}_saved_only` };
  if (chance(0.3)) out[rint(0, out.length - 1)].quota = randomQuota();
  if (chance(0.3)) {
    const s = out[rint(0, out.length - 1)];
    if (chance(0.5)) {
      s.facebook_targeting = { ...s.facebook_targeting, [pick(CORE_KEYS)]: randomTargetingValue() };
    } else {
      const keys = Object.keys(s.facebook_targeting);
      if (keys.length) delete s.facebook_targeting[pick(keys)];
    }
  }
  if (chance(0.3)) {
    const s = out[rint(0, out.length - 1)];
    s.facebook_targeting = reorderKeys(s.facebook_targeting);
  }
  if (chance(0.4)) {
    const s = out[rint(0, out.length - 1)];
    s.creatives = Array.from({ length: rint(0, 2) }, (_, i) => `saved_creative_${i}`);
    s.audiences = Array.from({ length: rint(0, 2) }, (_, i) => `saved_audience_${i}`);
    s.excluded_audiences = Array.from({ length: rint(0, 2) }, (_, i) => `saved_excluded_${i}`);
  }
  if (chance(0.15)) out.push({ ...copy(out[0]), id: `${out[0].id}_extra` });
  return out;
}

// Changes a staleness check must NOT notice: key order (it compares with
// lodash isEqual, not JSON.stringify), user-edited creatives/audiences, quota
// jitter below the 1e-9 tolerance, unknown fields. Without these, the random
// staleness cases are overwhelmingly `true` and the interesting direction —
// "the port agrees this is still fresh" — goes untested.
function benignPerturbStrata(fresh: any[]): any[] {
  const out: any[] = copy(fresh);
  for (const s of out) {
    if (chance(0.6)) s.facebook_targeting = reorderKeys(s.facebook_targeting);
    if (chance(0.4)) {
      s.creatives = Array.from({ length: rint(0, 2) }, (_, i) => `saved_creative_${i}`);
      s.audiences = Array.from({ length: rint(0, 2) }, (_, i) => `saved_audience_${i}`);
      s.excluded_audiences = Array.from({ length: rint(0, 2) }, (_, i) => `saved_excluded_${i}`);
    }
    if (chance(0.3)) s.quota = s.quota + 1e-12;
    if (chance(0.2)) s.metadata = { ...s.metadata, saved_only_field: 'x' };
  }
  return out;
}

const RANDOM_STRATA_CASES = 500;
for (let i = 0; i < RANDOM_STRATA_CASES; i++) {
  const vars = randomVariables();
  const ref = chance(0.1) ? pick(['', 'finish_q']) : `finish_${rint(1, 5)}`;
  const creatives = chance(0.4) ? Array.from({ length: rint(0, 3) }, (_, k) => ({ name: `c${k}` })) : null;
  const audiences = chance(0.3) ? Array.from({ length: rint(0, 2) }, (_, k) => ({ name: `a${k}`, subtype: 'CUSTOM' })) : null;
  const roll = rand();

  // The mix is weighted for information per byte: a merge case carries a whole
  // extra strata list in its args, so it costs roughly twice a plain create,
  // and formatGroupProduct cases are the cheapest way to buy more coverage of
  // the id/metadata/targeting-merge core.
  if (roll < 0.32) {
    strata(`random/create-${i}`, 'create_strata_from_variables', [vars, ref, creatives, audiences, null]);
  } else if (roll < 0.48) {
    const fresh = createStrataFromVariables(copy(vars) as any, ref || 'finish_q');
    strata(`random/create-merge-${i}`, 'create_strata_from_variables', [
      vars, ref, creatives, audiences, perturbStrata(fresh as any[]),
    ]);
  } else if (roll < 0.72) {
    const fresh = createStrataFromVariables(copy(vars) as any, 'finish_q') as any[];
    const mode = rand();
    let saved: any[];
    let useVars = vars;
    if (mode < 0.25) {
      saved = copy(fresh);                       // nothing changed
    } else if (mode < 0.5) {
      saved = benignPerturbStrata(fresh);        // changed in ways staleness ignores
    } else {
      saved = perturbStrata(fresh);
      if (chance(0.45)) useVars = mutateVariables(vars);
    }
    strata(`random/staleness-${i}`, 'strata_staleness_hint', [useVars, saved.length ? saved : null]);
  } else if (roll < 0.94) {
    // format_group_product on a non-empty level list (an empty one throws).
    const levels = vars
      .filter((v: any) => v.levels.length)
      .map((v: any) => ({ ...v.levels[rint(0, v.levels.length - 1)], variableName: v.name }));
    if (levels.length) {
      strata(`random/format-group-product-${i}`, 'format_group_product', [levels, ref]);
    } else {
      strata(`random/create-${i}-fallback`, 'create_strata_from_variables', [vars, ref, creatives, audiences, null]);
    }
  } else {
    const fresh = createStrataFromVariables(copy(vars) as any, ref || 'finish_q') as any[];
    strata(`random/finish-ref-${i}`, 'get_finish_question_ref', [fresh.length ? perturbStrata(fresh) : []]);
  }
}

const RANDOM_EXTRACT_CASES = 500;
for (let i = 0; i < RANDOM_EXTRACT_CASES; i++) {
  const roll = rand();
  if (roll < 0.4) {
    const targeting = randomTargeting();
    if (chance(0.5)) targeting.targeting_automation = { advantage_audience: pick([0, 1]), individual_setting: { age: 1 } };
    const present = Object.keys(targeting);
    const properties = shuffled(present).slice(0, rint(0, present.length));
    if (chance(0.3)) properties.push(pick([...CORE_KEYS, ...EXTRA_KEYS, 'custom_audiences']));
    const adset: any = { id: `adset-${i}`, targeting };
    if (chance(0.85)) adset.name = chance(0.1) ? '' : `Adset ${i}`;
    extract(`random/extract-${i}`, 'extract_from_adset', [chance(0.03) ? null : adset, shuffled(properties)]);
  } else if (roll < 0.7) {
    const stored = randomTargeting();
    let wouldApply: any = copy(stored);
    switch (rint(0, 4)) {
      case 0: break;                                            // identical
      case 1: wouldApply = reorderKeys(wouldApply); break;       // key order only
      case 2: wouldApply.targeting_automation = { advantage_audience: 0 }; break;
      case 3: {                                                  // a value drifts
        const keys = Object.keys(wouldApply);
        if (keys.length) wouldApply[pick(keys)] = randomTargetingValue();
        else wouldApply.age_min = rint(13, 65);
        break;
      }
      default: wouldApply[pick(EXTRA_KEYS)] = randomTargetingValue(); break;  // extra key
    }
    if (chance(0.05)) wouldApply = null;
    extract(`random/in-sync-${i}`, 'is_level_in_sync', [chance(0.05) ? null : stored, wouldApply]);
  } else {
    const stored = randomTargeting();
    if (chance(0.4)) stored.targeting_automation = { advantage_audience: 0 };
    const storedKeys = Object.keys(stored).filter(k => k !== 'targeting_automation');
    let current = shuffled(storedKeys);
    switch (rint(0, 3)) {
      case 0: break;                                             // same set
      case 1: current = current.slice(0, Math.max(0, current.length - 1)); break;
      case 2: current.push(pick([...CORE_KEYS, ...EXTRA_KEYS])); break;
      default: current = shuffled([...CORE_KEYS, ...EXTRA_KEYS]).slice(0, rint(0, 4)); break;
    }
    extract(`random/diff-keys-${i}`, 'diff_property_keys', [chance(0.04) ? null : stored, current]);
  }
}

// ---------------------------------------------------------------------------

const doc = {
  generated_by: `dashboard/scripts/authoring-conformance.ts (mulberry32 seed ${SEED})`,
  strata: strataCases,
  extract: extractCases,
};

process.stdout.write(JSON.stringify(doc, null, 1) + '\n');

const errors = extractCases.filter(c => 'error' in c).length;
process.stderr.write(
  `strata cases: ${strataCases.length}\n` +
  `extract cases: ${extractCases.length} (${errors} recording a thrown error)\n` +
  `total: ${strataCases.length + extractCases.length}\n`
);
