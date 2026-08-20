// The `additional_metadata` field is a JSON object typed into a text box, so
// the form has to hold two things at once: the raw text the user is midway
// through typing, and the parsed object that goes into the conf. They diverge
// while the JSON is incomplete — `{"foo"` is not parseable but is a perfectly
// normal thing to have typed — and the rule is that a half-typed value must
// never clear what is already saved.
//
// Extracted as a pure function so the three-way behaviour below is testable
// without mounting a form. Messenger.tsx still has its own inline copy; it is
// being edited on another branch, so it is left alone rather than churned.
// Fold it in when that lands.

export type ParsedMetadata =
  | { kind: 'empty' }
  | { kind: 'invalid' }
  | { kind: 'parsed'; value: Record<string, string> };

/**
 * Interpret the contents of the additional_metadata text box.
 *
 *  - `empty`   — the field was cleared. The caller writes `null` into the conf,
 *                not `{}`: adopt treats a missing additional_metadata as "no
 *                extra keys", and an empty object would be a different thing to
 *                round-trip.
 *  - `invalid` — not parseable yet. The caller keeps the text and leaves the
 *                conf alone, so typing does not destroy a saved value.
 *  - `parsed`  — a JSON object. Every key and value ends up as a dot-separated
 *                token in the ad's ref, which is why only objects are accepted:
 *                an array or a bare number has nothing to name its keys with.
 */
export function parseAdditionalMetadata(value: string): ParsedMetadata {
  if (!value) return { kind: 'empty' };

  let parsed: unknown;

  try {
    parsed = JSON.parse(value);
  } catch (e) {
    return { kind: 'invalid' };
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return { kind: 'invalid' };
  }

  return { kind: 'parsed', value: parsed as Record<string, string> };
}

/** What the text box shows for a conf that already has a value. */
export function metadataToText(
  metadata: Record<string, string> | null | undefined
): string {
  return metadata ? JSON.stringify(metadata) : '';
}
