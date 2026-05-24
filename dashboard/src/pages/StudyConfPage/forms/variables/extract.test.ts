import {
  extractFromAdset,
  AdsetNotFoundError,
  PropertyMissingError,
} from './extract';

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
        targeting_automation: 'DEFAULT',
      },
    };

    it('should extract requested properties from an adset', () => {
      const result = extractFromAdset(mockAdset, ['geo_locations', 'age_min', 'age_max']);

      expect(result).toEqual({
        geo_locations: { cities: [{ key: 'NG-BA', name: 'Bauchi' }] },
        age_min: 18,
        age_max: 65,
        targeting_automation: 'DEFAULT',
      });
    });

    it('should include targeting_automation if present, even if not requested', () => {
      const result = extractFromAdset(mockAdset, ['geo_locations']);

      expect(result).toHaveProperty('targeting_automation', 'DEFAULT');
    });

    it('should throw AdsetNotFoundError if adset is null', () => {
      expect(() => {
        extractFromAdset(null, ['geo_locations']);
      }).toThrow(AdsetNotFoundError);

      try {
        extractFromAdset(null, ['geo_locations']);
      } catch (err) {
        if (err instanceof AdsetNotFoundError) {
          expect(err.adsetName).toBe('(unknown)');
        }
      }
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

      try {
        extractFromAdset(mockAdset, ['custom_audiences']);
      } catch (err) {
        if (err instanceof PropertyMissingError) {
          expect(err.propertyKey).toBe('custom_audiences');
          expect(err.adsetName).toBe('Test Adset');
        }
      }
    });

    it('should return empty object for adset with targeting_automation but no requested properties', () => {
      const minimalAdset = {
        id: 'adset-456',
        name: 'Minimal Adset',
        targeting: {
          targeting_automation: 'DEFAULT',
        },
      };

      const result = extractFromAdset(minimalAdset, []);
      expect(result).toEqual({ targeting_automation: 'DEFAULT' });
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
});
