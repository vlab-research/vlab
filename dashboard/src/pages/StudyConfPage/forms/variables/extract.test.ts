import {
  extractFromAdset,
  propertiesOnSomeLevel,
  expectedPropertyKeys,
  AdsetNotFoundError,
  PropertyMissingError,
  isLevelInSync,
  diffPropertyKeys,
} from './extract';

const getError = (fn: () => any): Error => {
  try {
    fn();
    throw new Error('Expected function to throw');
  } catch (err) {
    return err as Error;
  }
};

describe('extract.ts', () => {
  describe('extractFromAdset', () => {
    const mockAdset = {
      id: 'adset-123',
      name: 'Test Adset',
      targeting: {
        geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi' }] },
        age_min: 18,
        age_max: 65,
        genders: [1],
        targeting_automation: {
          advantage_audience: 1,
          individual_setting: { age: 1, gender: 0, geo: 0 },
        },
      },
    };

    it('should extract requested properties from an adset', () => {
      const result = extractFromAdset(mockAdset, [
        'geo_locations',
        'age_min',
        'age_max',
      ]);

      expect(result).toEqual({
        geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi' }] },
        age_min: 18,
        age_max: 65,
        targeting_automation: { advantage_audience: 0 },
      });
    });

    it('should always force targeting_automation to {advantage_audience: 0}, stripping individual_setting from source', () => {
      const result = extractFromAdset(mockAdset, ['geo_locations']);

      expect(result.targeting_automation).toEqual({ advantage_audience: 0 });
      expect(result.targeting_automation).not.toHaveProperty(
        'individual_setting'
      );
    });

    it('should always include targeting_automation even if not present on source adset', () => {
      const adsetWithoutTA = {
        ...mockAdset,
        targeting: { ...mockAdset.targeting, targeting_automation: undefined },
      };

      const result = extractFromAdset(adsetWithoutTA, ['geo_locations']);

      expect(result.targeting_automation).toEqual({ advantage_audience: 0 });
    });

    it('should handle source adset with advantage_audience already 0 and no individual_setting', () => {
      const adsetAlreadyDisabled = {
        ...mockAdset,
        targeting: {
          ...mockAdset.targeting,
          targeting_automation: { advantage_audience: 0 },
        },
      };

      const result = extractFromAdset(adsetAlreadyDisabled, ['geo_locations']);

      expect(result.targeting_automation).toEqual({ advantage_audience: 0 });
    });

    it('should throw AdsetNotFoundError if adset is null', () => {
      expect(() => {
        extractFromAdset(null, ['geo_locations']);
      }).toThrow(AdsetNotFoundError);

      const err = getError(() => extractFromAdset(null, ['geo_locations']));
      expect(err).toBeInstanceOf(AdsetNotFoundError);
      expect((err as AdsetNotFoundError).adsetName).toBe('(unknown)');
    });

    it('should throw AdsetNotFoundError if adset is undefined', () => {
      expect(() => {
        extractFromAdset(undefined, ['geo_locations']);
      }).toThrow(AdsetNotFoundError);
    });

    it('should throw PropertyMissingError if a requested property is missing', () => {
      expect(() => {
        extractFromAdset(mockAdset, ['geo_locations', 'custom_audiences']);
      }).toThrow(PropertyMissingError);

      const err = getError(() =>
        extractFromAdset(mockAdset, ['custom_audiences'])
      );
      expect(err).toBeInstanceOf(PropertyMissingError);
      expect((err as PropertyMissingError).propertyKey).toBe(
        'custom_audiences'
      );
      expect((err as PropertyMissingError).adsetName).toBe('Test Adset');
    });

    it('should return only targeting_automation for adset with no requested properties', () => {
      const minimalAdset = {
        id: 'adset-456',
        name: 'Minimal Adset',
        targeting: {
          targeting_automation: {
            advantage_audience: 1,
            individual_setting: { age: 1 },
          },
        },
      };

      const result = extractFromAdset(minimalAdset, []);
      expect(result).toEqual({
        targeting_automation: { advantage_audience: 0 },
      });
    });

    it('should omit a missing property that is optional rather than throw', () => {
      const result = extractFromAdset(
        mockAdset,
        ['geo_locations', 'custom_audiences'],
        ['custom_audiences']
      );

      expect(result).toEqual({
        geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi' }] },
        targeting_automation: { advantage_audience: 0 },
      });
      expect('custom_audiences' in result).toBe(false);
    });

    it('should copy an optional property when the adset has it', () => {
      const result = extractFromAdset(
        mockAdset,
        ['geo_locations', 'age_min'],
        ['age_min']
      );

      expect(result.age_min).toBe(18);
    });

    it('should still throw for a missing property that is not optional', () => {
      const error = getError(() =>
        extractFromAdset(
          mockAdset,
          ['custom_audiences', 'excluded_geo_locations'],
          ['custom_audiences']
        )
      );

      expect(error).toBeInstanceOf(PropertyMissingError);
      expect((error as PropertyMissingError).propertyKey).toBe(
        'excluded_geo_locations'
      );
    });
  });

  // The rule behind `optional`: a property is required of every level only
  // when no level has it. One level with it makes it optional for the rest.
  describe('propertiesOnSomeLevel', () => {
    const urban = {
      id: 'adset-urban',
      name: 'Argentina - Urban',
      targeting: {
        geo_locations: { regions: [{ key: '1', name: 'Buenos Aires' }] },
        excluded_geo_locations: { regions: [{ key: '2', name: 'Pampa' }] },
      },
    };
    const rural = {
      id: 'adset-rural',
      name: 'Argentina - Rural',
      targeting: { geo_locations: { regions: [{ key: '2', name: 'Pampa' }] } },
    };
    const levels = [
      { template_adset: 'adset-urban' },
      { template_adset: 'adset-rural' },
    ];

    it('returns the properties at least one level carries', () => {
      const result = propertiesOnSomeLevel(
        levels,
        [urban, rural],
        ['geo_locations', 'excluded_geo_locations', 'custom_audiences']
      );

      expect(result).toEqual(['geo_locations', 'excluded_geo_locations']);
    });

    it('leaves out a property no level carries, so it stays required', () => {
      expect(
        propertiesOnSomeLevel(levels, [urban, rural], ['custom_audiences'])
      ).toEqual([]);
    });

    it('lets a level lacking the property extract once another level has it', () => {
      const optional = propertiesOnSomeLevel(
        levels,
        [urban, rural],
        ['geo_locations', 'excluded_geo_locations']
      );
      const result = extractFromAdset(
        rural,
        ['geo_locations', 'excluded_geo_locations'],
        optional
      );

      expect(result).toEqual({
        geo_locations: { regions: [{ key: '2', name: 'Pampa' }] },
        targeting_automation: { advantage_audience: 0 },
      });
    });

    it('ignores a level whose adset is not found', () => {
      const result = propertiesOnSomeLevel(
        [{ template_adset: 'adset-rural' }, { template_adset: 'adset-gone' }],
        [urban, rural],
        ['geo_locations', 'excluded_geo_locations']
      );

      expect(result).toEqual(['geo_locations']);
    });

    it('ignores an adset with no targeting object', () => {
      const bare = { id: 'adset-bare', name: 'Bare' };

      expect(
        propertiesOnSomeLevel(
          [{ template_adset: 'adset-bare' }],
          [bare],
          ['geo_locations']
        )
      ).toEqual([]);
    });

    it('keeps the order of properties, not of levels', () => {
      const result = propertiesOnSomeLevel(
        levels,
        [urban, rural],
        ['excluded_geo_locations', 'geo_locations']
      );

      expect(result).toEqual(['excluded_geo_locations', 'geo_locations']);
    });
  });

  describe('expectedPropertyKeys', () => {
    it('drops the properties wouldApply omitted', () => {
      const wouldApply = {
        geo_locations: {},
        targeting_automation: { advantage_audience: 0 },
      };

      expect(
        expectedPropertyKeys(wouldApply, [
          'geo_locations',
          'excluded_geo_locations',
        ])
      ).toEqual(['geo_locations']);
    });

    it('falls back to all properties when there is nothing that would apply', () => {
      expect(expectedPropertyKeys(null, ['geo_locations'])).toEqual([
        'geo_locations',
      ]);
    });
  });

  describe('error types', () => {
    it('AdsetNotFoundError should have correct name and adsetName field', () => {
      const error = new AdsetNotFoundError('my-adset');
      expect(error.name).toBe('AdsetNotFoundError');
      expect(error.adsetName).toBe('my-adset');
      expect(error.message).toContain('my-adset');
    });

    it('PropertyMissingError should have correct name and fields', () => {
      const error = new PropertyMissingError('my-adset', 'geo_locations');
      expect(error.name).toBe('PropertyMissingError');
      expect(error.adsetName).toBe('my-adset');
      expect(error.propertyKey).toBe('geo_locations');
      expect(error.message).toContain('geo_locations');
    });
  });

  describe('isLevelInSync', () => {
    it('returns true when stored and wouldApply are equal', () => {
      const obj = { age_min: 18, geo_locations: { countries: ['US'] } };
      expect(isLevelInSync(obj, obj)).toBe(true);
    });

    it('returns true when top-level keys are in different orders with the same content', () => {
      const stored = {
        age_max: 45,
        age_min: 18,
        geo_locations: { countries: ['NG'] },
      };
      const wouldApply = {
        age_min: 18,
        age_max: 45,
        geo_locations: { countries: ['NG'] },
      };
      expect(isLevelInSync(stored, wouldApply)).toBe(true);
    });

    it('returns true when nested keys are in different orders with the same content', () => {
      const stored = {
        geo_locations: { countries: ['NG'], location_types: ['home'] },
      };
      const wouldApply = {
        geo_locations: { location_types: ['home'], countries: ['NG'] },
      };
      expect(isLevelInSync(stored, wouldApply)).toBe(true);
    });

    it('ignores targeting_automation when comparing', () => {
      const stored = { age_min: 18 };
      const wouldApply = {
        age_min: 18,
        targeting_automation: { advantage_audience: 0 },
      };
      expect(isLevelInSync(stored, wouldApply)).toBe(true);
    });

    it('returns false when values differ for the same key', () => {
      const stored = { age_min: 18 };
      const wouldApply = { age_min: 25 };
      expect(isLevelInSync(stored, wouldApply)).toBe(false);
    });

    it('returns false when stored is empty and wouldApply has values', () => {
      expect(isLevelInSync({}, { age_min: 18 })).toBe(false);
    });

    it('returns true when both stored and wouldApply are empty', () => {
      expect(isLevelInSync({}, {})).toBe(true);
    });

    it('handles null or non-object inputs without throwing', () => {
      expect(isLevelInSync(null, null)).toBe(true);
      expect(isLevelInSync(undefined, undefined)).toBe(true);
      expect(isLevelInSync(null, { age_min: 18 })).toBe(false);
    });
  });

  describe('diffPropertyKeys', () => {
    it('returns no diff when stored keys match current properties', () => {
      const stored = {
        age_min: 18,
        genders: [1],
        targeting_automation: { advantage_audience: 0 },
      };
      expect(diffPropertyKeys(stored, ['age_min', 'genders'])).toEqual({
        added: [],
        removed: [],
        keysDiffer: false,
      });
    });

    it('detects added properties', () => {
      const stored = { age_min: 18 };
      expect(diffPropertyKeys(stored, ['age_min', 'genders'])).toEqual({
        added: ['genders'],
        removed: [],
        keysDiffer: true,
      });
    });

    it('detects removed properties', () => {
      const stored = { age_min: 18, genders: [1] };
      expect(diffPropertyKeys(stored, ['age_min'])).toEqual({
        added: [],
        removed: ['genders'],
        keysDiffer: true,
      });
    });

    it('treats empty current as removing all stored keys', () => {
      const stored = { age_min: 18, genders: [1] };
      expect(diffPropertyKeys(stored, [])).toEqual({
        added: [],
        removed: ['age_min', 'genders'],
        keysDiffer: true,
      });
    });

    it('ignores targeting_automation when computing stored keys', () => {
      const stored = {
        age_min: 18,
        targeting_automation: { advantage_audience: 0 },
      };
      expect(diffPropertyKeys(stored, ['age_min'])).toEqual({
        added: [],
        removed: [],
        keysDiffer: false,
      });
    });

    it('does not mutate the input stored object', () => {
      const stored = {
        age_min: 18,
        targeting_automation: { advantage_audience: 0 },
      };
      const snapshot = JSON.stringify(stored);
      diffPropertyKeys(stored, ['age_min']);
      expect(JSON.stringify(stored)).toEqual(snapshot);
    });

    it('handles null or non-object inputs without throwing', () => {
      expect(diffPropertyKeys(null, ['age_min'])).toEqual({
        added: ['age_min'],
        removed: [],
        keysDiffer: true,
      });
      expect(diffPropertyKeys(undefined, [])).toEqual({
        added: [],
        removed: [],
        keysDiffer: false,
      });
    });
  });
});
