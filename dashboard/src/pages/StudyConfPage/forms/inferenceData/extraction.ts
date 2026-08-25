/**
 * Pure logic for the extraction-conf form, for every source.
 * No React dependencies; testable in isolation.
 *
 * An extraction conf tells swoosh where to find one variable, in two parts:
 *
 *   location  where to read      — `variable` (walk a path into the response
 *                                  the respondent produced) or `metadata`
 *                                  (look up a key in what the connector
 *                                  stamped on the event)
 *   mapping   what that means    — `raw` (the value read IS the answer) or
 *                                  `ad_table_lookup` (the value read is an
 *                                  opaque token identifying the ad that
 *                                  recruited them; the answer is a stratum
 *                                  variable off that ad's frozen row)
 *
 * The two are independent, which is why one module serves every source. A
 * respondent recruited by a fly destination brings the token back in event
 * metadata; one recruited by a web or app destination lands on the researcher's
 * own page and brings it back as a field in Typeform or Qualtrics. Each conf
 * declares where its own token is.
 *
 * `metadata` is a *keyed* read under either mapping: you name a key and get a
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

export const locationOptions = [
  { name: '', label: 'Where is the data located in the source?' },
  { name: METADATA_LOCATION, label: 'Metadata' },
  { name: VARIABLE_LOCATION, label: 'Variable' },
];

/** What to do with the value read from the location. */
export const mappingOptions = [
  { name: RAW_MAPPING, label: 'Use the value as it is' },
  { name: AD_TABLE_LOOKUP_MAPPING, label: 'Ad (which ad recruited them)' },
];

export const isAdTableLookup = (data: Extraction): boolean =>
  data.mapping === AD_TABLE_LOOKUP_MAPPING;

/**
 * The response values a source's payload offers, for the one location that has
 * a path to walk. fly events carry the answer and its translation; Qualtrics
 * and Typeform answers carry a label and a value.
 */
export const responseOptions = (source: string) =>
  source === 'fly'
    ? [
        { name: 'response', label: 'Response' },
        { name: 'translated_response', label: 'Translated Response' },
      ]
    : [
        { name: 'label', label: 'Label' },
        { name: 'value', label: 'Value' },
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

/**
 * What `key` means, which is contextual to the mapping.
 *
 * For a lookup it addresses the TOKEN, not the stratum variable — the stratum
 * variable is `name`, which does double duty. Getting this backwards is the
 * easy mistake, so the placeholder says which one it wants.
 */
export const keyPlaceholder = (data: Extraction): string => {
  if (isAdTableLookup(data)) {
    return 'Which key or field carries the ad token? On fly: vt';
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
 * Switching to a keyed location resets `functions` to the identity select.
 * Without it, a conf built as `variable` with `path: "response"` would keep
 * trying to select "response" out of a bare metadata value and fail extraction
 * for every event.
 *
 * The mapping is left alone by a location change. Location says where to read
 * and mapping says what the value means, and a conf can read its token from
 * either place, so a change of location says nothing about what was read.
 *
 * `aggregate` is derived from the conf's own location on every change rather
 * than pinned to "first". Pinned, an edit to any other field would quietly
 * demote a `variable` conf back to the first value it ever saw — so a survey
 * answer someone corrected mid-study would keep the answer they corrected.
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
    aggregate: aggregateForLocation(data.location),
    mapping: data.mapping || RAW_MAPPING,
    ...update,
  };
};
