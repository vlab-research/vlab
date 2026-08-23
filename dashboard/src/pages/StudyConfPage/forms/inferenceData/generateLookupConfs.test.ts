import {
  DEFAULT_TOKEN_KEY,
  blankExtractionConf,
  initialExtractionConfs,
  lookupConfsFromVariables,
} from './generateLookupConfs';
import { AD_TABLE_LOOKUP_MAPPING } from './flyExtraction';

describe('generateLookupConfs', () => {
  describe('lookupConfsFromVariables', () => {
    it('produces one lookup conf per declared variable', () => {
      const confs = lookupConfsFromVariables(['gender', 'Age', 'Region']);
      expect(confs.map(c => c.name)).toEqual(['gender', 'Age', 'Region']);
    });

    it('reads the token from metadata under the ad lookup mapping', () => {
      const [conf] = lookupConfsFromVariables(['gender']);

      expect(conf.location).toBe('metadata');
      expect(conf.mapping).toBe(AD_TABLE_LOOKUP_MAPPING);
      expect(conf.key).toBe(DEFAULT_TOKEN_KEY);
    });

    it('names the conf after the stratum variable, which is also the row key', () => {
      // `name` does double duty: the output variable AND the key into the ad's
      // frozen row. Defaulting from the variables conf is safe precisely
      // because those are one string and cannot drift.
      const [conf] = lookupConfsFromVariables(['gender']);
      expect(conf.name).toBe('gender');
    });

    it('takes the first value for a keyed read', () => {
      // You attribute someone to the ad that recruited them, so a later value
      // cannot supersede an earlier one.
      const [conf] = lookupConfsFromVariables(['gender']);
      expect(conf.aggregate).toBe('first');
    });

    it('uses the identity select, since metadata has no response path', () => {
      const [conf] = lookupConfsFromVariables(['gender']);
      expect(conf.functions).toEqual([
        { function: 'select', params: { path: '' } },
      ]);
    });

    it('emits one token key across every conf, never a disagreement', () => {
      // Confs under one source that name different keys attribute nobody, and
      // silently — a token that is not there looks like an organic arrival.
      const keys = lookupConfsFromVariables(['gender', 'Age', 'Region']).map(
        c => c.key
      );
      expect(new Set(keys).size).toBe(1);
    });

    it('honours an explicit token key', () => {
      // swoosh never hardcodes metadata.vt; the conf declares where the token
      // is, so a platform surfacing it elsewhere just says so.
      const [conf] = lookupConfsFromVariables(['gender'], 'token');
      expect(conf.key).toBe('token');
    });

    it('ignores empty variable names', () => {
      expect(lookupConfsFromVariables(['', 'gender', ''])).toHaveLength(1);
    });

    it('produces nothing for a study with no variables', () => {
      expect(lookupConfsFromVariables([])).toEqual([]);
    });
  });

  describe('initialExtractionConfs', () => {
    it('defaults a fly source to one lookup per declared variable', () => {
      const confs = initialExtractionConfs('fly', ['gender', 'Age']);

      expect(confs.map(c => c.name)).toEqual(['gender', 'Age']);
      expect(confs.every(c => c.mapping === AD_TABLE_LOOKUP_MAPPING)).toBe(true);
    });

    it('leaves other sources with a blank row', () => {
      // Qualtrics and Typeform carry no ad token, so a lookup conf there would
      // silently yield nothing forever.
      expect(initialExtractionConfs('qualtrics', ['gender'])).toEqual([
        blankExtractionConf(),
      ]);
      expect(initialExtractionConfs('typeform', ['gender'])).toEqual([
        blankExtractionConf(),
      ]);
    });

    it('falls back to a blank row when the study declares no variables', () => {
      // An empty list would render nothing at all and look broken.
      expect(initialExtractionConfs('fly', [])).toEqual([blankExtractionConf()]);
    });
  });

  describe('blankExtractionConf', () => {
    it('is empty in every field, so the form validates it as unfilled', () => {
      const blank = blankExtractionConf();

      expect(blank.name).toBe('');
      expect(blank.location).toBe('');
      expect(blank.key).toBe('');
      expect(blank.functions).toEqual([]);
    });

    it('is a fresh object each time', () => {
      // It is appended to a list on every Add; a shared reference would make
      // two rows edit each other.
      expect(blankExtractionConf()).not.toBe(blankExtractionConf());
    });
  });
});
