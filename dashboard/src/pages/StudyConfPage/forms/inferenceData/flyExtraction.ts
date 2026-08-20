/**
 * Pure logic for the fly source's extraction-conf form.
 * No React dependencies; testable in isolation.
 *
 * An extraction conf tells swoosh where to find one variable, in two parts:
 *
 *   location  where to read      — `variable` (walk a path into the response
 *                                  the respondent produced) or `metadata`
 *                                  (look up a key in what fly stamped on the
 *                                  event)
 *   mapping   what that means    — `raw` (the value read IS the answer) or
 *                                  `ad_table_lookup` (the value read is an
 *                                  opaque token identifying the ad that
 *                                  recruited them; the answer is a stratum
 *                                  variable off that ad's frozen row)
 *
 * There is no `ad` location and there never really was one: the token lives in
 * metadata, so reading it is an ordinary metadata read. What makes a variable
 * ad-derived is the mapping. The old `ad` location joined on ad_id and has been
 * removed — see documentation/ad-attributions.md.
 *
 * `metadata` is a *keyed* lookup under either mapping: you name a key and get a
 * value, so there is no response path to select. `variable` is the only
 * location with one. Most of the branching in this form is really that
 * distinction, so it is expressed once, here.
 */
import { Extraction } from '../../../../types/conf';

export const METADATA_LOCATION = 'metadata';
export const VARIABLE_LOCATION = 'variable';

export const RAW_MAPPING = 'raw';
export const AD_TABLE_LOOKUP_MAPPING = 'ad_table_lookup';

/**
 * Locations whose value is found by key rather than by walking a response path.
 * Only `metadata` — but kept as a named concept because the form branches on
 * "is there a response to select?", not on the location's name.
 */
export const KEYED_LOCATIONS = [METADATA_LOCATION];

export const isKeyedLocation = (location: string): boolean =>
  KEYED_LOCATIONS.includes(location);

/**
 * The locations a fly-sourced variable can come from.
 *
 * Shared in shape with the Qualtrics/Typeform form now that `ad` is gone. They
 * are still separate modules, because what is fly-only is the *mapping* — see
 * mappingOptions.
 */
export const locationOptions = [
  { name: '', label: 'Where is the data located in the source?' },
  { name: METADATA_LOCATION, label: 'Metadata' },
  { name: VARIABLE_LOCATION, label: 'Variable' },
];

/**
 * What to do with the value read from metadata.
 *
 * Deliberately NOT shared with the Qualtrics/Typeform form. A lookup needs the
 * source to carry the ad token, and only fly does; offering it on a Qualtrics
 * source would let someone configure a variable that silently yields nothing
 * forever — exactly the quiet miscount this design exists to prevent.
 *
 * This is the seam that opens without a structural change: a platform that
 * starts surfacing the token just adds this option to its own form and declares
 * whichever metadata key it arrives under.
 */
export const mappingOptions = [
  { name: RAW_MAPPING, label: 'Use the value as it is' },
  { name: AD_TABLE_LOOKUP_MAPPING, label: 'Ad (which ad recruited them)' },
];

/** The mapping choice only makes sense for a metadata read. */
export const showsMapping = (location: string): boolean =>
  location === METADATA_LOCATION;

export const isAdTableLookup = (data: Extraction): boolean =>
  data.mapping === AD_TABLE_LOOKUP_MAPPING;

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

/**
 * What `key` means, which is contextual to the mapping.
 *
 * For a lookup it addresses the TOKEN, not the stratum variable — the stratum
 * variable is `name`, which does double duty. Getting this backwards is the
 * easy mistake, so the placeholder says which one it wants.
 */
export const keyPlaceholder = (data: Extraction): string => {
  if (isAdTableLookup(data)) {
    return 'Which metadata key carries the ad token? Usually: vt';
  }
  return 'What is the variable called in the data source?';
};

/**
 * What `name` means. For a lookup it is both the output name and the stratum
 * variable pulled off the ad's frozen row, so it has to match a key the study's
 * ads were actually built with.
 */
export const namePrompt = (data: Extraction): string =>
  isAdTableLookup(data)
    ? 'Which stratum variable? e.g. creative, gender, Age (also its name here)'
    : 'What name do you use to refer to this variable?';

export const responsePrompt = (location: string): string =>
  isKeyedLocation(location)
    ? 'Not needed — this value is looked up by key'
    : 'Which response value do you want to use?';

/**
 * Compute the next extraction conf from one form field change.
 *
 * Two resets, both guarding against a stale field surviving a change of mind:
 *
 * Switching to a keyed location resets `functions` to the identity select.
 * Without it, a conf built as `variable` with `path: "response"` would keep
 * trying to select "response" out of a bare metadata value and fail extraction
 * for every event.
 *
 * Switching AWAY from metadata resets `mapping` to raw. Without it, a conf
 * could end up `variable` + `ad_table_lookup`, which is rejected at config time
 * — and worse, its `key` would look like a declaration of where the token
 * lives, which is how a study ends up classifying every respondent against the
 * wrong metadata key.
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
        mapping: showsMapping(value) ? data.mapping || RAW_MAPPING : RAW_MAPPING,
      };
      break;

    default:
      update = { [name]: value } as Partial<Extraction>;
  }

  return {
    ...data,
    value_type: 'categorical',
    aggregate: 'first',
    mapping: data.mapping || RAW_MAPPING,
    ...update,
  };
};
