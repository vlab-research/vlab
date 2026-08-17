/**
 * Pure config for the Qualtrics/Typeform extraction form.
 * No React dependencies; testable in isolation.
 *
 * Kept as its own list rather than shared with flyExtraction, deliberately.
 * The two forms look almost identical and it is tempting to merge them, but
 * only the fly connector populates an event's ad id — the Qualtrics and
 * Typeform connectors do not. Offering `location: "ad"` here would let someone
 * configure a variable that silently yields nothing forever, which is exactly
 * the quiet miscount the ad-ID design exists to prevent.
 *
 * If these forms are ever merged, the locations have to stay per-source.
 * flyExtraction.test.ts asserts this list does not contain `ad`.
 */
export const locationOptions = [
  { name: '', label: 'Where is the data located in the source?' },
  { name: 'metadata', label: 'Metadata' },
  { name: 'variable', label: 'Variable' },
];
