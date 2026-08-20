/**
 * Pure config for the Qualtrics/Typeform extraction form.
 * No React dependencies; testable in isolation.
 *
 * The locations are the same two fly offers now that `ad` is gone. What stays
 * per-source is the *mapping*: fly offers `ad_table_lookup`, and this form
 * offers no mapping choice at all, because only fly carries the ad token that a
 * lookup joins on. Offering it here would let someone configure a variable that
 * silently yields nothing forever, which is exactly the quiet miscount the
 * ad-attribution design exists to prevent.
 *
 * Kept as its own module for that reason. If these forms are ever merged, the
 * mapping options have to stay per-source — flyExtraction.test.ts asserts this
 * module exposes none.
 */
export const locationOptions = [
  { name: '', label: 'Where is the data located in the source?' },
  { name: 'metadata', label: 'Metadata' },
  { name: 'variable', label: 'Variable' },
];

/**
 * Deliberately empty, and deliberately exported. A Qualtrics or Typeform source
 * cannot produce the ad token, so it gets no mapping choice — the conf is
 * always a raw read. Exported so the guard test can assert the absence rather
 * than the module merely not mentioning it.
 */
export const mappingOptions: { name: string; label: string }[] = [];
