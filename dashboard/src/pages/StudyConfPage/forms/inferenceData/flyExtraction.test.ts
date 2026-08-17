import {
  AD_LOCATION,
  applyChange,
  aggregateForLocation,
  isKeyedLocation,
  keyPlaceholder,
  locationOptions,
  responsePrompt,
} from './flyExtraction';
import { locationOptions as qualtricsLocationOptions } from './qualtricsExtraction';
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

describe('flyExtraction', () => {
  describe('locationOptions', () => {
    it('offers ad alongside metadata and variable', () => {
      expect(locationOptions.map(o => o.name)).toEqual([
        '',
        'metadata',
        'variable',
        'ad',
      ]);
    });

    it('labels ad in researcher language, not ad-id jargon', () => {
      const ad = locationOptions.find(o => o.name === AD_LOCATION);
      expect(ad?.label).toBe('Ad (which ad recruited them)');
      expect(ad?.label).not.toMatch(/ad_id|attribution|mapping/i);
    });
  });

  describe('aggregateForLocation', () => {
    // Ad-derived and metadata-derived values are recruitment-time constants:
    // you attribute someone to the ad that recruited them. Only a survey
    // answer can meaningfully be updated later.
    it('gives ad "first", exactly like metadata', () => {
      expect(aggregateForLocation('ad')).toBe('first');
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
    it('treats ad and metadata as keyed, variable as not', () => {
      expect(isKeyedLocation('ad')).toBe(true);
      expect(isKeyedLocation('metadata')).toBe(true);
      expect(isKeyedLocation('variable')).toBe(false);
      expect(isKeyedLocation('')).toBe(false);
    });
  });

  describe('applyChange', () => {
    it('sets aggregate "first" when ad is selected', () => {
      const result = applyChange(blank(), 'location', 'ad');
      expect(result.location).toBe('ad');
      expect(result.aggregate).toBe('first');
    });

    it('sets aggregate "last" when variable is selected', () => {
      expect(applyChange(blank(), 'location', 'variable').aggregate).toBe('last');
    });

    it('resets a stale response path when switching to ad', () => {
      // The bug this prevents: a conf built as `variable` with
      // path "response", then switched to `ad`, would keep trying to select
      // "response" out of a bare metadata string and fail extraction for
      // every single event.
      const stale = blank({
        location: 'variable',
        functions: [{ function: 'select', params: { path: 'response' } }],
      });

      const result = applyChange(stale, 'location', 'ad');

      expect(result.functions).toEqual([
        { function: 'select', params: { path: '' } },
      ]);
    });

    it('resets a stale response path when switching to metadata too', () => {
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
      expect(applyChange(blank(), 'key', 'gender').key).toBe('gender');
      expect(applyChange(blank(), 'name', 'md:gender').name).toBe('md:gender');
    });

    it('always sets value_type categorical', () => {
      expect(applyChange(blank(), 'location', 'ad').value_type).toBe('categorical');
    });
  });

  describe('placeholders', () => {
    it('asks for a stratum metadata key when the location is ad', () => {
      // For an ad-derived variable the key is one of the stratum metadata keys
      // the study's ads were built with, not a field in the survey data.
      expect(keyPlaceholder('ad')).toMatch(/ad metadata key/i);
      expect(keyPlaceholder('ad')).toMatch(/creative/);
    });

    it('keeps the data-source wording for other locations', () => {
      expect(keyPlaceholder('variable')).toBe(
        'What is the variable called in the data source?'
      );
      expect(keyPlaceholder('metadata')).toBe(
        'What is the variable called in the data source?'
      );
    });

    it('explains that keyed locations need no response', () => {
      expect(responsePrompt('ad')).toMatch(/looked up by key/i);
      expect(responsePrompt('metadata')).toMatch(/looked up by key/i);
      expect(responsePrompt('variable')).toBe(
        'Which response value do you want to use?'
      );
    });
  });

  describe('the ad location is fly-only', () => {
    it('is absent from the Qualtrics/Typeform form', () => {
      // Only the fly connector populates an event's ad id. Offering `ad` on a
      // Qualtrics or Typeform source would let someone configure a variable
      // that silently yields nothing forever — the exact quiet miscount the
      // ad-ID design exists to prevent. If these ever get merged into one
      // shared component, this test is the thing that should stop it.
      expect(qualtricsLocationOptions.map(o => o.name)).not.toContain('ad');
      expect(qualtricsLocationOptions.map(o => o.name)).toEqual([
        '',
        'metadata',
        'variable',
      ]);
    });
  });

  describe('round trip into what swoosh reads', () => {
    it('produces a conf shaped exactly as the "ad" retrieve function expects', () => {
      // swoosh's getRetrieveFunc switches on `location`, retrieveFromAd looks
      // up `key` in the frozen ad_attributions metadata blob, addValue
      // resolves repeats by `aggregate`, and the variable lands under `name`.
      // This is the whole contract the form has to satisfy.
      let conf = blank();
      conf = applyChange(conf, 'name', 'md:gender');
      conf = applyChange(conf, 'location', 'ad');
      conf = applyChange(conf, 'key', 'gender');

      expect(conf).toEqual({
        name: 'md:gender',
        location: 'ad',
        key: 'gender',
        functions: [{ function: 'select', params: { path: '' } }],
        aggregate: 'first',
        value_type: 'categorical',
      });
    });
  });
});
