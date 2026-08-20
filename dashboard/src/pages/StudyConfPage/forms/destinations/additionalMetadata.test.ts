import { metadataToText, parseAdditionalMetadata } from './additionalMetadata';

describe('parseAdditionalMetadata', () => {
  it('parses a JSON object', () => {
    expect(parseAdditionalMetadata('{"wave": "2"}')).toEqual({
      kind: 'parsed',
      value: { wave: '2' },
    });
  });

  it('reports an empty field so the caller can write null, not {}', () => {
    // adopt treats a missing additional_metadata as "no extra keys". An empty
    // object is a different thing and would not round-trip the same way.
    expect(parseAdditionalMetadata('')).toEqual({ kind: 'empty' });
  });

  it('reports half-typed JSON as invalid rather than empty', () => {
    // THE case this function exists for. Every one of these is a keystroke on
    // the way to valid JSON, and treating any of them as "cleared" would wipe a
    // saved value while the user is still typing.
    for (const partial of ['{', '{"wave"', '{"wave":', '{"wave": "2"']) {
      expect(parseAdditionalMetadata(partial)).toEqual({ kind: 'invalid' });
    }
  });

  it('rejects valid JSON that is not an object', () => {
    // Each key and value becomes a dot-separated token in the ad's ref, so a
    // bare scalar or an array has nothing to name its keys with.
    for (const notAnObject of ['"foo"', '3', 'null', '[1, 2]', 'true']) {
      expect(parseAdditionalMetadata(notAnObject)).toEqual({ kind: 'invalid' });
    }
  });

  it('accepts an explicitly empty object as parsed, not empty', () => {
    // `{}` is something the user typed on purpose; `` is a cleared field.
    expect(parseAdditionalMetadata('{}')).toEqual({ kind: 'parsed', value: {} });
  });
});

describe('metadataToText', () => {
  it('renders a saved value back into the text box', () => {
    expect(metadataToText({ wave: '2' })).toEqual('{"wave":"2"}');
  });

  it('renders an absent value as an empty box', () => {
    expect(metadataToText(null)).toEqual('');
    expect(metadataToText(undefined)).toEqual('');
  });

  it('round-trips through the parser', () => {
    const original = { wave: '2', country: 'NG' };
    expect(parseAdditionalMetadata(metadataToText(original))).toEqual({
      kind: 'parsed',
      value: original,
    });
  });
});
