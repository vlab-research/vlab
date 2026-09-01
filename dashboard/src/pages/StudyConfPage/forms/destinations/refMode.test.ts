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

  it('names them, rather than describing them', () => {
    // The control used to answer a question with two sentences and no names,
    // which left a researcher nothing to refer to afterwards. These are the
    // defined terms, and they are the same ones the docs use.
    expect(refModeOptions().map(o => o.label)).toEqual([
      'Plain ref',
      'Encoded ref',
    ]);
  });

  it('defines each name where it is chosen', () => {
    // A term is useless without its definition, and the moment of choosing is
    // the only moment the researcher is looking. Every option carries one.
    for (const option of refModeOptions()) {
      expect(option.description).toBeTruthy();
    }
  });

  it('says where the stratum data comes out, on both sides of the choice', () => {
    // The one thing that decides it. Plain puts it in the response columns;
    // encoded puts it in a separate export, and names the key to join on,
    // because a researcher will not guess `ref_token`.
    const [plain, encoded] = refModeOptions();

    expect(plain.description).toMatch(/columns/i);
    expect(encoded.description).toMatch(/ad-attributions export/i);
    expect(encoded.description).toMatch(/ref_token/);
  });

  it('warns that a plain ref is readable where the respondent can see it', () => {
    // Its one cost, and the whole reason a WhatsApp study cannot take it.
    expect(refModeOptions()[0].description).toMatch(/whatsapp/i);
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
