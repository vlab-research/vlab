/**
 * Pure logic for the fly source's extraction-conf form.
 * No React dependencies; testable in isolation.
 *
 * An extraction conf tells swoosh where to find one variable. `location` picks
 * the strategy, and the three of them split two ways:
 *
 *   variable  — walk a path into the response payload the respondent produced
 *   metadata  — look up a key in the metadata fly stamped on the event
 *   ad        — look up a key in the frozen ad_attributions row for the ad
 *               that recruited the respondent
 *
 * `metadata` and `ad` are both *keyed* lookups: you name a key and get a value.
 * `variable` is the only one with a response path to select. Most of the
 * branching in this form is really that distinction, so it is expressed once,
 * here, rather than as scattered `=== "metadata"` checks.
 *
 * See documentation/ad-attributions.md for the ad -> stratum join.
 */
import { Extraction } from '../../../../types/conf';

export const AD_LOCATION = 'ad';
export const METADATA_LOCATION = 'metadata';
export const VARIABLE_LOCATION = 'variable';

/**
 * Locations whose value is found by key rather than by walking a response path.
 * Both read a key out of a blob — `metadata` out of the event's, `ad` out of
 * the ad's frozen metadata — so neither has a response to select.
 */
export const KEYED_LOCATIONS = [METADATA_LOCATION, AD_LOCATION];

export const isKeyedLocation = (location: string): boolean =>
  KEYED_LOCATIONS.includes(location);

/**
 * The locations a fly-sourced variable can come from.
 *
 * Deliberately NOT shared with the Qualtrics/Typeform form. Only the fly
 * connector populates an event's ad id, so offering `ad` there would let
 * someone configure a variable that silently yields nothing forever — which is
 * exactly the quiet miscount the ad-ID design exists to prevent.
 */
export const locationOptions = [
  { name: '', label: 'Where is the data located in the source?' },
  { name: METADATA_LOCATION, label: 'Metadata' },
  { name: VARIABLE_LOCATION, label: 'Variable' },
  { name: AD_LOCATION, label: 'Ad (which ad recruited them)' },
];

/**
 * How repeat values for one respondent are resolved.
 *
 * Keyed locations are recruitment-time constants — you attribute someone to
 * the ad that recruited them, and to the metadata they arrived with — so the
 * first value wins. Only a survey answer can meaningfully be updated later,
 * so only `variable` takes the last.
 */
export const aggregateForLocation = (location: string): string =>
  location === VARIABLE_LOCATION ? 'last' : 'first';

/** The identity extraction: take the retrieved value exactly as it is. */
export const identityFunctions = () => [
  { function: 'select', params: { path: '' } },
];

export const selectFunctions = (path: string) => [
  { function: 'select', params: { path } },
];

export const keyPlaceholder = (location: string): string =>
  location === AD_LOCATION
    ? 'Which ad metadata key? e.g. creative, gender, Age'
    : 'What is the variable called in the data source?';

export const responsePrompt = (location: string): string =>
  isKeyedLocation(location)
    ? 'Not needed — this value is looked up by key'
    : 'Which response value do you want to use?';

/**
 * Compute the next extraction conf from one form field change.
 *
 * Switching to a keyed location resets `functions` to the identity select.
 * Without that, a conf that had been `variable` with `path: "response"` would
 * keep trying to select "response" out of a bare metadata value and fail
 * extraction for every event. (The Qualtrics form already does this for
 * `metadata`; here it applies to both keyed locations.)
 */
export const applyChange = (
  data: Extraction,
  name: string,
  value: string
): Extraction => {
  let update: Partial<Extraction>;

  switch (name) {
    case 'response':
      update = { functions: selectFunctions(value) };
      break;

    case 'location':
      update = {
        location: value,
        aggregate: aggregateForLocation(value),
        functions: isKeyedLocation(value) ? identityFunctions() : data.functions,
      };
      break;

    default:
      update = { [name]: value } as Partial<Extraction>;
  }

  return {
    ...data,
    value_type: 'categorical',
    aggregate: 'first',
    ...update,
  };
};
