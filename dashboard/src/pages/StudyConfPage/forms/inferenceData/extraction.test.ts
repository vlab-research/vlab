import {
  AD_TABLE_LOOKUP_MAPPING,
  applyChange,
  aggregateForLocation,
  isAdTableLookup,
  isKeyedLocation,
  keyPlaceholder,
  locationOptions,
  mappingOptions,
  namePrompt,
  responseOptions,
  responsePrompt,
} from './extraction';
import { generateLookupConfs } from './generateLookupConfs';
import { Extraction } from '../../../../types/conf';

const blank = (overrides: Partial<Extraction> = {}): Extraction => ({
  name: '',
  location: '',
  key: '',
  functions: [],
  aggregate: '',
  value_type: '',
  ...overrides,
});

const lookup = (overrides: Partial<Extraction> = {}): Extraction =>
  blank({ location: 'metadata', mapping: AD_TABLE_LOOKUP_MAPPING, ...overrides });

describe('extraction', () => {
  describe('locationOptions', () => {
    it('offers metadata and variable', () => {
      expect(locationOptions.map((o: { name: string }) => o.name)).toEqual([
        '',
        'metadata',
        'variable',
      ]);
    });
  });

  describe('mappingOptions', () => {
    it('offers the raw read and the ad lookup', () => {
      expect(mappingOptions.map((o: { name: string }) => o.name)).toEqual([
        'raw',
        'ad_table_lookup',
      ]);
    });

    it('labels the lookup in researcher language, not join jargon', () => {
      const ad = mappingOptions.find(
        (o: { name: string }) => o.name === AD_TABLE_LOOKUP_MAPPING
      );
      expect(ad?.label).toBe('Ad (which ad recruited them)');
      expect(ad?.label).not.toMatch(/ad_id|token|attribution|join/i);
    });
  });

  describe('responseOptions', () => {
    // The one thing a source still decides: what its payload offers to walk
    // into. A fly event carries the answer and its translation; a Qualtrics or
    // Typeform answer carries a label and a value.
    it('offers a fly event its response and translation', () => {
      expect(responseOptions('fly').map(o => o.name)).toEqual([
        'response',
        'translated_response',
      ]);
    });

    it('offers a survey answer its label and value', () => {
      expect(responseOptions('qualtrics').map(o => o.name)).toEqual([
        'label',
        'value',
      ]);
      expect(responseOptions('typeform').map(o => o.name)).toEqual([
        'label',
        'value',
      ]);
    });
  });

  describe('aggregateForLocation', () => {
    // Metadata-derived values are recruitment-time constants: you attribute
    // someone to the ad that recruited them, and to the metadata they arrived
    // with. Only a survey answer can meaningfully be updated later.
    it('gives metadata "first"', () => {
      expect(aggregateForLocation('metadata')).toBe('first');
    });

    it('gives variable "last"', () => {
      expect(aggregateForLocation('variable')).toBe('last');
    });

    it('does not let an unrecognised location fall through to "last"', () => {
      // The old form read `location === "metadata" ? "first" : "last"`, so
      // every new location silently became "last". The condition is inverted
      // now so that only `variable` — the one location whose value genuinely
      // changes over time — takes the later value.
      expect(aggregateForLocation('')).toBe('first');
      expect(aggregateForLocation('something_new')).toBe('first');
    });
  });

  describe('isKeyedLocation', () => {
    it('treats metadata as keyed and variable as not', () => {
      expect(isKeyedLocation('metadata')).toBe(true);
      expect(isKeyedLocation('variable')).toBe(false);
      expect(isKeyedLocation('')).toBe(false);
    });
  });

  describe('isAdTableLookup', () => {
    it('is true only for the lookup mapping', () => {
      expect(isAdTableLookup(lookup())).toBe(true);
      expect(isAdTableLookup(blank({ location: 'metadata', mapping: 'raw' }))).toBe(false);
      expect(isAdTableLookup(blank({ location: 'metadata' }))).toBe(false);
    });
  });

  describe('applyChange', () => {
    it('defaults the mapping to raw', () => {
      // Absent means raw everywhere that reads it, so a conf stored before this
      // field existed keeps meaning what it meant.
      expect(applyChange(blank(), 'key', 'gender').mapping).toBe('raw');
    });

    it('sets aggregate "first" when metadata is selected', () => {
      const result = applyChange(blank(), 'location', 'metadata');
      expect(result.location).toBe('metadata');
      expect(result.aggregate).toBe('first');
    });

    it('sets aggregate "last" when variable is selected', () => {
      expect(applyChange(blank(), 'location', 'variable').aggregate).toBe('last');
    });

    it('sets the lookup mapping when it is chosen', () => {
      const result = applyChange(
        blank({ location: 'metadata' }),
        'mapping',
        AD_TABLE_LOOKUP_MAPPING
      );
      expect(result.mapping).toBe(AD_TABLE_LOOKUP_MAPPING);
    });

    it('keeps the lookup mapping while the location stays metadata', () => {
      expect(applyChange(lookup(), 'location', 'metadata').mapping).toBe(
        AD_TABLE_LOOKUP_MAPPING
      );
    });

    it('leaves the mapping alone when the location changes', () => {
      // Location says where to read and mapping says what the value means, and
      // a lookup can read its token from either place. A respondent recruited
      // by a web or app destination lands on the researcher's own page and
      // brings the token back as a survey field.
      expect(applyChange(lookup(), 'location', 'variable').mapping).toBe(
        AD_TABLE_LOOKUP_MAPPING
      );
    });

    it('resets a stale response path when switching to metadata', () => {
      // A conf built as `variable` with path "response", then switched, would
      // keep trying to select "response" out of a bare metadata string and fail
      // extraction for every single event.
      const stale = blank({
        location: 'variable',
        functions: [{ function: 'select', params: { path: 'response' } }],
      });

      expect(applyChange(stale, 'location', 'metadata').functions).toEqual([
        { function: 'select', params: { path: '' } },
      ]);
    });

    it('keeps the response path when switching to variable', () => {
      const existing = blank({
        location: 'metadata',
        functions: [{ function: 'select', params: { path: 'translated_response' } }],
      });

      expect(applyChange(existing, 'location', 'variable').functions).toEqual([
        { function: 'select', params: { path: 'translated_response' } },
      ]);
    });

    it('sets the response path from the response field', () => {
      const result = applyChange(blank(), 'response', 'translated_response');
      expect(result.functions).toEqual([
        { function: 'select', params: { path: 'translated_response' } },
      ]);
    });

    it('keeps a variable conf on "last" through an unrelated edit', () => {
      // `aggregate` follows the conf's own location on every change. Pinned to
      // "first", editing any other field would quietly demote a `variable`
      // conf back to the first value it ever saw, so a survey answer someone
      // corrected mid-study would keep the answer they corrected.
      const existing = blank({ location: 'variable', aggregate: 'last' });

      expect(applyChange(existing, 'key', 'q1').aggregate).toBe('last');
    });

    it('passes other fields straight through', () => {
      expect(applyChange(blank(), 'key', 'vt').key).toBe('vt');
      expect(applyChange(blank(), 'name', 'gender').name).toBe('gender');
    });

    it('always sets value_type categorical', () => {
      expect(applyChange(blank(), 'location', 'metadata').value_type).toBe(
        'categorical'
      );
    });
  });

  describe('prompts', () => {
    it('asks for the token when the mapping is a lookup', () => {
      // For a lookup, `key` addresses the TOKEN, not the stratum variable.
      // Getting this backwards is the easy mistake, so the prompt says which.
      expect(keyPlaceholder(lookup())).toMatch(/token/i);
      expect(keyPlaceholder(lookup())).toMatch(/vt/);
    });

    it('asks for the token on a variable lookup too', () => {
      expect(
        keyPlaceholder(lookup({ location: 'variable', key: 'vlab_token' }))
      ).toMatch(/token/i);
    });

    it('keeps the data-source wording for a raw read', () => {
      expect(keyPlaceholder(blank({ location: 'variable' }))).toBe(
        'What is the variable called in the data source?'
      );
      expect(keyPlaceholder(blank({ location: 'metadata' }))).toBe(
        'What is the variable called in the data source?'
      );
    });

    it('asks for a stratum variable as the name of a lookup', () => {
      // `name` does double duty for a lookup: the output name AND the key into
      // the ad's frozen row, so it has to be a key the ads were built with.
      expect(namePrompt(lookup())).toMatch(/stratum variable/i);
      expect(namePrompt(lookup())).toMatch(/creative/);
    });

    it('keeps the ordinary naming wording otherwise', () => {
      expect(namePrompt(blank())).toBe(
        'What name do you use to refer to this variable?'
      );
    });

    it('explains that keyed locations need no response', () => {
      expect(responsePrompt('metadata')).toMatch(/looked up by key/i);
      expect(responsePrompt('variable')).toBe(
        'Which response value do you want to use?'
      );
    });
  });

  describe('generateLookupConfs', () => {
    // A fly source with nothing saved starts with one lookup per variable the
    // researcher already declared in Variables. The name is exactly what the
    // ad's frozen row is keyed by, so asking for them again in a different
    // vocabulary is what produces a silent half-config.
    it('gives a fly source one lookup conf per declared variable', () => {
      const confs = generateLookupConfs('fly', ['gender', 'Age']);

      expect(confs).toEqual([
        {
          name: 'gender',
          location: 'metadata',
          mapping: 'ad_table_lookup',
          key: 'vt',
          functions: [{ function: 'select', params: { path: '' } }],
          aggregate: 'first',
          value_type: 'categorical',
        },
        {
          name: 'Age',
          location: 'metadata',
          mapping: 'ad_table_lookup',
          key: 'vt',
          functions: [{ function: 'select', params: { path: '' } }],
          aggregate: 'first',
          value_type: 'categorical',
        },
      ]);
    });

    it('gives another source one blank row', () => {
      // The default has to guess where the token is, and `vt` is fly's
      // convention. Another source returns it as a field only the researcher
      // can name.
      const confs = generateLookupConfs('qualtrics', ['gender', 'Age']);

      expect(confs).toHaveLength(1);
      expect(confs[0].name).toBe('');
      expect(confs[0].mapping).toBe('raw');
    });

    it('gives a fly source with no variables one blank row', () => {
      expect(generateLookupConfs('fly', [])).toHaveLength(1);
    });

    it('skips a variable the researcher has not named yet', () => {
      // `name` is both the output name and the key into the ad's frozen row, so
      // a lookup without one reads nothing off the row while presenting itself
      // as configured.
      const confs = generateLookupConfs('fly', ['gender', '', 'Age']);

      expect(confs.map(c => c.name)).toEqual(['gender', 'Age']);
    });

    it('falls back to a blank row when no variable is named', () => {
      // One unnamed variable is length 1, so a length check lets it through.
      const confs = generateLookupConfs('fly', ['']);

      expect(confs).toHaveLength(1);
      expect(confs[0].name).toBe('');
      expect(confs[0].mapping).toBe('raw');
      expect(confs[0].location).toBe('');
    });
  });

  describe('round trip into what swoosh reads', () => {
    it('produces a conf shaped exactly as the lookup expects', () => {
      // swoosh's getRetrieveFunc composes the location's reader with the
      // mapping: the reader takes `key` (the token), resolveThroughAdTable
      // joins it against ad_attributions.ref_token, and `name` comes off the
      // frozen row — which is also what the variable is called. addValue
      // resolves repeats by `aggregate`. This is the whole contract the form
      // has to satisfy.
      let conf = blank();
      conf = applyChange(conf, 'name', 'gender');
      conf = applyChange(conf, 'location', 'metadata');
      conf = applyChange(conf, 'mapping', AD_TABLE_LOOKUP_MAPPING);
      conf = applyChange(conf, 'key', 'vt');

      expect(conf).toEqual({
        name: 'gender',
        location: 'metadata',
        mapping: 'ad_table_lookup',
        key: 'vt',
        functions: [{ function: 'select', params: { path: '' } }],
        aggregate: 'first',
        value_type: 'categorical',
      });
    });

    it('produces an unchanged raw conf, as every existing study has', () => {
      let conf = blank();
      conf = applyChange(conf, 'name', 'md:gender');
      conf = applyChange(conf, 'location', 'metadata');
      conf = applyChange(conf, 'key', 'gender');

      expect(conf).toEqual({
        name: 'md:gender',
        location: 'metadata',
        mapping: 'raw',
        key: 'gender',
        functions: [{ function: 'select', params: { path: '' } }],
        aggregate: 'first',
        value_type: 'categorical',
      });
    });
  });

  describe('a lookup on a survey field', () => {
    it('produces the conf a web- or app-recruited study needs', () => {
      // The respondent landed on the researcher's own page, so their token
      // comes back as a Typeform or Qualtrics field rather than as metadata a
      // connector stamped. Same mapping, same frozen row, different reader.
      let conf = blank();
      conf = applyChange(conf, 'name', 'gender');
      conf = applyChange(conf, 'location', 'variable');
      conf = applyChange(conf, 'mapping', AD_TABLE_LOOKUP_MAPPING);
      conf = applyChange(conf, 'key', 'vlab_token');
      conf = applyChange(conf, 'response', '');

      expect(conf).toEqual({
        name: 'gender',
        location: 'variable',
        mapping: 'ad_table_lookup',
        key: 'vlab_token',
        functions: [{ function: 'select', params: { path: '' } }],
        aggregate: 'last',
        value_type: 'categorical',
      });
    });
  });
});
