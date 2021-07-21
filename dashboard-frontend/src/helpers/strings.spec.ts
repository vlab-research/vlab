import React from 'react';
import { createSlugFor, classNames } from './strings';

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
