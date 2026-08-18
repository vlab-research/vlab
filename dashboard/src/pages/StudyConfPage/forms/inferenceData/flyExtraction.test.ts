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
  responsePrompt,
  showsMapping,
} from './flyExtraction';
import {
  locationOptions as qualtricsLocationOptions,
  mappingOptions as qualtricsMappingOptions,
} from './qualtricsExtraction';
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

describe('flyExtraction', () => {
  describe('locationOptions', () => {
    it('offers metadata and variable, and no longer an ad location', () => {
      // There is no `ad` location and there never really was one: the token
      // lives in metadata, so reading it is an ordinary metadata read. The old
      // `ad` location joined on ad_id and is removed.
      expect(locationOptions.map(o => o.name)).toEqual([
        '',
        'metadata',
        'variable',
      ]);
    });
  });

  describe('mappingOptions', () => {
    it('offers the raw read and the ad lookup', () => {
      expect(mappingOptions.map(o => o.name)).toEqual(['raw', 'ad_table_lookup']);
    });

    it('labels the lookup in researcher language, not join jargon', () => {
      const ad = mappingOptions.find(o => o.name === AD_TABLE_LOOKUP_MAPPING);
      expect(ad?.label).toBe('Ad (which ad recruited them)');
      expect(ad?.label).not.toMatch(/ad_id|token|attribution|join/i);
    });

    it('is only offered for a metadata read', () => {
      // The mapping says what to do with a metadata value. There is nothing for
      // it to mean on a survey response.
      expect(showsMapping('metadata')).toBe(true);
      expect(showsMapping('variable')).toBe(false);
      expect(showsMapping('')).toBe(false);
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

    it('resets the mapping to raw when switching away from metadata', () => {
      // The bug this prevents: a conf left as `variable` + `ad_table_lookup` is
      // rejected at config time — and worse, its `key` would look like a
      // declaration of where the ad token lives, which is how a study ends up
      // classifying every respondent against the wrong metadata key.
      expect(applyChange(lookup(), 'location', 'variable').mapping).toBe('raw');
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
    it('asks for the token key when the mapping is a lookup', () => {
      // For a lookup, `key` addresses the TOKEN, not the stratum variable.
      // Getting this backwards is the easy mistake, so the prompt says which.
      expect(keyPlaceholder(lookup())).toMatch(/token/i);
      expect(keyPlaceholder(lookup())).toMatch(/vt/);
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

  describe('the ad lookup is fly-only', () => {
    it('is absent from the Qualtrics/Typeform form', () => {
      // A lookup joins on the ad token, and only the fly connector carries one.
      // Offering it on a Qualtrics or Typeform source would let someone
      // configure a variable that silently yields nothing forever — the exact
      // quiet miscount this design exists to prevent. If these ever get merged
      // into one shared component, this test is the thing that should stop it.
      expect(qualtricsMappingOptions).toEqual([]);
      expect(qualtricsLocationOptions.map(o => o.name)).toEqual([
        '',
        'metadata',
        'variable',
      ]);
      expect(qualtricsLocationOptions.map(o => o.name)).not.toContain('ad');
    });
  });

  describe('round trip into what swoosh reads', () => {
    it('produces a conf shaped exactly as the lookup expects', () => {
      // swoosh's getRetrieveFunc switches on `location`, retrieveFromMetadata
      // reads `key` (the token) out of the event metadata, joins it against
      // ad_attributions.ref_token, and takes `name` off the frozen row — which
      // is also what the variable is called. addValue resolves repeats by
      // `aggregate`. This is the whole contract the form has to satisfy.
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
});
