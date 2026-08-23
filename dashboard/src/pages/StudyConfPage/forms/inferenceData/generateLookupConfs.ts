/**
 * What the extraction form starts with for a source that has none saved.
 *
 * A stratified ad study attributes its respondents — you do not opt into that,
 * it is the task. The researcher already named their stratum variables in
 * **Variables**, and those names are exactly what the ad's frozen
 * `ad_attributions` row is keyed by. Asking for them again, in a different form
 * and a different vocabulary (`location`, `mapping`, `key`, `name`), is the
 * split that produces silent half-configs: a study whose ads carry a token
 * nothing looks up, discovered hours later in a swoosh log.
 *
 * So a fly source's confs default to one lookup per declared variable, in place
 * of the single blank row the form used to seed. That is all this is — a
 * default. It renders as ordinary editable rows and is overwritten the moment
 * the researcher saves anything of their own, because a saved conf is loaded in
 * preference to any default. There is no merging, and no second copy of these
 * confs held anywhere: either a source has saved confs and those are what you
 * see, or it does not and these are.
 *
 * See planning/ref-mode-dashboard-ux.md §7 and documentation/ad-attributions.md.
 */
import { Extraction } from '../../../../types/conf';
import {
  AD_TABLE_LOOKUP_MAPPING,
  METADATA_LOCATION,
  aggregateForLocation,
  identityFunctions,
} from './flyExtraction';

/**
 * Where fly stamps the ad token.
 *
 * A convention, not a constant of the system: swoosh never assumes the token is
 * at metadata.vt, the conf's `key` declares where it is. One key is used across
 * every conf produced here, which is what keeps this from ever creating the
 * disagreement `disagreeing_token_keys` warns about — one respondent has one
 * token, in one place, and confs naming a different key attribute nobody,
 * silently, because a token that is not there looks like an organic arrival.
 */
export const DEFAULT_TOKEN_KEY = 'vt';

/** The blank row the form seeds with when it has nothing better to offer. */
export const blankExtractionConf = (): Extraction => ({
  name: '',
  location: '',
  key: '',
  functions: [],
  aggregate: '',
  value_type: '',
});

/**
 * One lookup conf per declared stratum variable.
 *
 * `name` does double duty, as it does everywhere in this mechanism: it is the
 * output variable name AND the key into the ad's frozen row. That is exactly
 * why defaulting from the variables conf is safe — the researcher named the
 * stratum variable, the ad was built with that name in its metadata, and the
 * conf asks for it back under the same name. The three cannot drift apart
 * because they are one string.
 *
 * `aggregate` comes from `aggregateForLocation`, which answers 'first' for a
 * keyed read: you attribute someone to the ad that recruited them, so a later
 * value cannot supersede an earlier one. `functions` is the identity select,
 * because a metadata read is keyed — there is no response path to walk.
 */
export const lookupConfsFromVariables = (
  variableNames: string[],
  tokenKey: string = DEFAULT_TOKEN_KEY
): Extraction[] =>
  variableNames
    .filter(name => !!name)
    .map(name => ({
      name,
      location: METADATA_LOCATION,
      mapping: AD_TABLE_LOOKUP_MAPPING,
      key: tokenKey,
      functions: identityFunctions(),
      value_type: 'categorical',
      aggregate: aggregateForLocation(METADATA_LOCATION),
    }));

/**
 * The confs a source starts with, before the researcher touches anything.
 *
 * Lookups are defaulted on **fly sources only**, for the same reason the ad
 * lookup mapping is offered on fly sources only: Qualtrics and Typeform carry
 * no ad token, so a lookup conf there would silently yield nothing forever.
 * Every other source keeps the blank row.
 */
export const initialExtractionConfs = (
  sourceType: string,
  variableNames: string[]
): Extraction[] => {
  if (sourceType !== 'fly') return [blankExtractionConf()];

  const lookups = lookupConfsFromVariables(variableNames);

  return lookups.length ? lookups : [blankExtractionConf()];
};
