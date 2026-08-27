/**
 * The extraction confs a fly source starts with.
 *
 * A fly source with nothing saved starts with one `ad_table_lookup` conf per
 * variable declared in Variables, in place of a single blank row. The
 * researcher already named those variables, and the name is exactly what the
 * ad's frozen row is keyed by — `name` does double duty for a lookup, as the
 * output name and as the stratum variable pulled off the row — so asking for
 * them again in a different vocabulary is what produces a silent half-config.
 *
 * A default, not a merge: a source with saved confs shows those, a source
 * without shows these, nothing merges, and no second copy is held anywhere.
 *
 * Fly only. The default has to guess where the token is, and `vt` is fly's
 * convention: fly decodes the encoded ref locally and stamps the token there.
 * Another source returns it as a field only the researcher can name.
 */
import { Extraction } from '../../../../types/conf';
import {
  AD_TABLE_LOOKUP_MAPPING,
  METADATA_LOCATION,
  RAW_MAPPING,
  identityFunctions,
} from './extraction';

/** Where fly stamps the token it decoded out of the ref. */
export const FLY_TOKEN_KEY = 'vt';

export const FLY_SOURCE = 'fly';

/** The one empty row a source falls back to when it has nothing to offer. */
export const blankConf = (): Extraction => ({
  name: '',
  location: '',
  key: '',
  functions: [],
  aggregate: '',
  value_type: '',
  mapping: RAW_MAPPING,
});

const lookupConf = (variable: string): Extraction => ({
  name: variable,
  location: METADATA_LOCATION,
  mapping: AD_TABLE_LOOKUP_MAPPING,
  key: FLY_TOKEN_KEY,
  functions: identityFunctions(),
  aggregate: 'first',
  value_type: 'categorical',
});

/**
 * What a source with nothing saved shows: a lookup per declared variable for
 * fly, and one blank row for anything else.
 */
export const generateLookupConfs = (
  source: string,
  variables: string[]
): Extraction[] => {
  if (source !== FLY_SOURCE) {
    return [blankConf()];
  }

  // An unnamed variable produces no conf. `name` is both the output name and
  // the key into the ad's frozen row, so a lookup without one reads nothing off
  // the row while presenting itself as configured — the researcher sees a
  // filled-in row that can only ever yield nothing.
  //
  // Filtered rather than counted: one unnamed variable is length 1, so a
  // `variables.length === 0` guard lets it straight through.
  const named = variables.filter(name => !!name);

  return named.length ? named.map(lookupConf) : [blankConf()];
};
