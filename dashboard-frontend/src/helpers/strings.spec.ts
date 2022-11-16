import {
  createSlugFor,
  classNames,
  toCamelCase,
  createLabelFor,
  createNameFor,
} from './strings';

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

describe('classNames', () => {
  it('returns a className by joining the provided strings with a whitespace', () => {
    expect(classNames('Button Button--big', 'Button--hollow')).toBe(
      'Button Button--big Button--hollow'
    );
    expect(classNames('Button', 'Button--big')).toBe('Button Button--big');
    expect(classNames('Button', '')).toBe('Button');
    expect(classNames('Button')).toBe('Button');
  });
});

describe('camelCase', () => {
  it('returns a string in camelCase', () => {
    expect(toCamelCase('')).toBe('');
    expect(toCamelCase('min_budget')).toBe('minBudget');
  });
});

describe('createLabelFor', () => {
  it('returns a capitalised string with white space before every capital letter', () => {
    expect(createLabelFor('')).toBe('');
    expect(createLabelFor('min_budget')).toBe('Min Budget');
  });
});

describe('createNameFor', () => {
  it('returns a lowercase string and replaces each white space with an underscore', () => {
    expect(createNameFor('')).toBe('');
    expect(createNameFor('Min Budget')).toBe('min_budget');
  });
});
