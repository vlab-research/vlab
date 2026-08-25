import {
  ENCODED_MODE,
  METADATA_MODE,
  displayedRefMode,
  refModeChanges,
  refModeOptions,
} from './refMode';

describe('refModeOptions', () => {
  it('offers both modes, from nothing', () => {
    // There is nothing to decide it from: what a ref carries is a property of
    // the ref, not of the channel carrying it.
    expect(refModeOptions().map(o => o.name)).toEqual([
      METADATA_MODE,
      ENCODED_MODE,
    ]);
  });

  it('labels by consequence, not by field value', () => {
    // What a researcher needs is where their stratum data ends up and what the
    // key is. The words `ref_mode` and `encoded` never reach the screen.
    for (const option of refModeOptions()) {
      expect(option.label).not.toMatch(/ref_mode|encoded|token|metadata/i);
    }

    expect(refModeOptions()[0].label).toMatch(/columns/i);
    expect(refModeOptions()[1].label).toMatch(/looked up/i);
  });
});

describe('displayedRefMode', () => {
  it('reports what a conf with no mode actually does', () => {
    // An absent ref_mode is a real state: the conf predates the field, and
    // resolves to the behaviour it already has.
    expect(displayedRefMode(undefined)).toBe(METADATA_MODE);
    expect(displayedRefMode('')).toBe(METADATA_MODE);
  });

  it('reports a stated mode as stated', () => {
    expect(displayedRefMode(METADATA_MODE)).toBe(METADATA_MODE);
    expect(displayedRefMode(ENCODED_MODE)).toBe(ENCODED_MODE);
  });
});

describe('refModeChanges', () => {
  it('treats an absent mode and an explicit metadata as the same thing', () => {
    // They describe the same ads, so saving one over the other rewrites
    // nothing and must not be warned about.
    expect(refModeChanges(undefined, METADATA_MODE)).toBe(false);
    expect(refModeChanges(METADATA_MODE, undefined)).toBe(false);
  });

  it('sees a real change in either direction', () => {
    expect(refModeChanges(undefined, ENCODED_MODE)).toBe(true);
    expect(refModeChanges(METADATA_MODE, ENCODED_MODE)).toBe(true);
    expect(refModeChanges(ENCODED_MODE, METADATA_MODE)).toBe(true);
  });

  it('sees no change when nothing moved', () => {
    expect(refModeChanges(ENCODED_MODE, ENCODED_MODE)).toBe(false);
  });
});
