import {
  DEFAULT_TOKEN_KEY,
  lookupConfsFromVariables,
  mergeLookupConfs,
  wouldGenerateAnything,
} from './generateLookupConfs';
import { AD_TABLE_LOOKUP_MAPPING } from './flyExtraction';
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
      // frozen row. Generating from the variables conf is safe precisely
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
      expect(conf.functions).toEqual([{ function: 'select', params: { path: '' } }]);
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

  describe('mergeLookupConfs', () => {
    const generated = lookupConfsFromVariables(['gender', 'Age']);

    it('adds generated confs to an empty form', () => {
      expect(mergeLookupConfs([], generated).map(c => c.name)).toEqual([
        'gender',
        'Age',
      ]);
    });

    it('drops the form\'s seeded blank row', () => {
      // Left in place it would fail validation on save, for a reason nobody
      // could see on screen.
      expect(mergeLookupConfs([blank()], generated)).toHaveLength(2);
    });

    it('never overwrites a conf the researcher already wrote', () => {
      // A study can perfectly reasonably read `gender` from a survey answer
      // rather than from the ad. Overwriting that would make the button a trap.
      const hand = blank({
        name: 'gender',
        location: 'variable',
        key: 'q_gender',
      });

      const merged = mergeLookupConfs([hand], generated);

      expect(merged.filter(c => c.name === 'gender')).toEqual([hand]);
      expect(merged.map(c => c.name)).toEqual(['gender', 'Age']);
    });

    it('is idempotent', () => {
      const once = mergeLookupConfs([], generated);
      expect(mergeLookupConfs(once, generated)).toEqual(once);
    });

    it('keeps unrelated confs untouched', () => {
      const unrelated = blank({ name: 'finished', location: 'variable' });
      const merged = mergeLookupConfs([unrelated], generated);

      expect(merged[0]).toEqual(unrelated);
      expect(merged).toHaveLength(3);
    });
  });

  describe('wouldGenerateAnything', () => {
    it('is true for a form holding only its seeded blank row', () => {
      // The case a naive length comparison gets wrong: merging drops the blank,
      // so the count is unchanged even though every variable would be added.
      expect(wouldGenerateAnything([blank()], ['gender'])).toBe(true);
    });

    it('is false once every declared variable has a row', () => {
      const confs = lookupConfsFromVariables(['gender', 'Age']);
      expect(wouldGenerateAnything(confs, ['gender', 'Age'])).toBe(false);
    });

    it('is false when the study declares no variables', () => {
      expect(wouldGenerateAnything([], [])).toBe(false);
    });

    it('is true when a variable was added after the last generation', () => {
      const confs = lookupConfsFromVariables(['gender']);
      expect(wouldGenerateAnything(confs, ['gender', 'Region'])).toBe(true);
    });

    it('counts a hand-written conf as covering its variable', () => {
      const hand = blank({ name: 'gender', location: 'variable' });
      expect(wouldGenerateAnything([hand], ['gender'])).toBe(false);
    });
  });
});
