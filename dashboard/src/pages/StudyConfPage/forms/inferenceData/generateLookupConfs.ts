/**
 * Generating the read side of ad attribution from what the study already
 * declared.
 *
 * A stratified ad study attributes its respondents — you do not opt into that,
 * it is the task. The researcher already named their stratum variables in
 * **Variables**, and those names are exactly what the ad's frozen
 * `ad_attributions` row is keyed by. Asking for them again, in a different
 * form, under a different vocabulary (`location`, `mapping`, `key`, `name`) is
 * the split that produces silent half-configs: a study whose ads carry a token
 * nothing looks up, discovered hours later in a swoosh log.
 *
 * So this module turns declared variables into lookup confs. It does not decide
 * *whether* to: that stays an explicit action in the form, and the generated
 * confs land as ordinary editable rows saved through the normal Submit. Nothing
 * is synthesised behind the researcher's back, and the stored conf stays the
 * whole truth about what swoosh will run.
 *
 * A study that wants to attribute on a variable it did NOT stratify on remains
 * a manual addition in the form — an addition, not the common path.
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
 * at metadata.vt, the conf's `key` declares where it is. Generation emits one
 * key across every conf it produces, which is what keeps it from ever creating
 * the disagreement `disagreeing_token_keys` warns about — one respondent has
 * one token, in one place, and confs naming a different key attribute nobody,
 * silently, because a token that is not there looks like an organic arrival.
 */
export const DEFAULT_TOKEN_KEY = 'vt';

/**
 * One lookup conf per declared stratum variable.
 *
 * `name` does double duty, as it does everywhere in this mechanism: it is the
 * output variable name AND the key into the ad's frozen row. That is exactly
 * why generation from the variables conf is safe — the researcher named the
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
 * Fold generated confs into what the form already holds.
 *
 * Additive by name, and never destructive. A conf the researcher has already
 * written for a variable — whatever its location or mapping — wins over the
 * generated one, because they may well have meant it: a study can perfectly
 * reasonably read `gender` from a survey answer rather than from the ad.
 * Overwriting that would make the button a trap, and a researcher who has to
 * check what a button destroyed will stop using it.
 *
 * Blank rows are dropped. The form seeds itself with one empty conf, so
 * generating into an untouched form would otherwise leave an empty row that
 * fails validation on save for a reason nobody could see.
 */
export const mergeLookupConfs = (
  existing: Extraction[],
  generated: Extraction[]
): Extraction[] => {
  const meaningful = existing.filter(isMeaningful);
  const claimed = new Set(meaningful.map(c => c.name));

  return [...meaningful, ...generated.filter(c => !claimed.has(c.name))];
};

/** A row the researcher has actually started filling in. */
const isMeaningful = (conf: Extraction): boolean =>
  !!(conf.name || conf.location || conf.key);

/**
 * Whether generating would actually add anything.
 *
 * Drives the button's disabled state, so a researcher can tell "already done"
 * from "nothing to do" without clicking and watching nothing happen.
 */
export const wouldGenerateAnything = (
  existing: Extraction[],
  variableNames: string[],
  tokenKey: string = DEFAULT_TOKEN_KEY
): boolean => {
  // Compared against the meaningful rows, not against `existing`: merging drops
  // blank rows, so a form still holding its seeded empty conf has the same
  // length before and after even though generating would add every variable.
  const claimed = new Set(existing.filter(isMeaningful).map(c => c.name));

  return lookupConfsFromVariables(variableNames, tokenKey).some(
    c => !claimed.has(c.name)
  );
};
