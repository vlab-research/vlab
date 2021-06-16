import { createSlugFor } from './strings';

describe('createSlugFor', () => {
  it('returns a slug for the given string', () => {
    expect(
      createSlugFor(`Saint
    Petersburg`)
    ).toBe('saint-petersburg');
    expect(createSlugFor('Saint  Petersburg')).toBe('saint-petersburg');
    expect(createSlugFor('Saint Petersburg')).toBe('saint-petersburg');
    expect(createSlugFor('St. Petersburg')).toBe('st.-petersburg');
    expect(createSlugFor('StPetersburg')).toBe('stpetersburg');
    expect(createSlugFor('Spain')).toBe('spain');
    expect(createSlugFor('')).toBe('');
  });
});
