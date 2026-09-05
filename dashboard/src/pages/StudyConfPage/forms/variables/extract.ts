/**
 * Pure extraction module for facebook_targeting from template adsets.
 * Typed error handling allows the UI to render specific, actionable messages.
 * No React dependencies; testable in isolation.
 */
import isEqual from 'lodash/isEqual';

export class AdsetNotFoundError extends Error {
  adsetName: string;

  constructor(adsetName: string) {
    super(`Template adset ${adsetName} not found on Meta`);
    this.adsetName = adsetName;
    this.name = 'AdsetNotFoundError';
  }
}

export class PropertyMissingError extends Error {
  adsetName: string;
  propertyKey: string;

  constructor(adsetName: string, propertyKey: string) {
    super(`Adset ${adsetName} has no ${propertyKey} property`);
    this.adsetName = adsetName;
    this.propertyKey = propertyKey;
    this.name = 'PropertyMissingError';
  }
}

/**
 * Extract requested properties from an adset's targeting.
 *
 * @param adset The adset object from the Meta API response. Must have id and targeting.
 * @param properties Array of property keys to extract (e.g. ["geo_locations", "age_min"])
 * @param optional Properties whose absence is tolerated: a missing one is left
 *   out of the result rather than thrown. See `propertiesOnSomeLevel` for
 *   where the caller gets this list.
 * @returns Object with extracted targeting properties
 * @throws AdsetNotFoundError if adset is null or undefined
 * @throws PropertyMissingError if a requested, non-optional property is not present on the adset
 */
export function extractFromAdset(
  adset: any | null | undefined,
  properties: string[],
  optional: string[] = []
): any {
  if (!adset) {
    throw new AdsetNotFoundError('(unknown)');
  }

  const extracted: any = {};

  for (const property of properties) {
    if (!(property in adset.targeting)) {
      if (optional.includes(property)) continue;
      throw new PropertyMissingError(adset.name || adset.id, property);
    }
    extracted[property] = adset.targeting[property];
  }

  // Always force Advantage+ Audience off. We never use Advantage+ audience — it
  // imposes constraints (e.g. age_min ≤ 25 as a "control" via individual_setting)
  // that we'd have to remember and validate against. By always sending
  // {advantage_audience: 0} without individual_setting, we avoid all Advantage+
  // audience rules while still using the targeting properties pulled from the
  // source adset. This is a deliberate policy decision, not a fallback.
  extracted.targeting_automation = { advantage_audience: 0 };

  return extracted;
}

/**
 * The subset of `properties` that at least one level's adset carries.
 *
 * A variable declares its properties once, but its levels come from
 * different adsets and Meta only writes a targeting key when it is set.
 * `excluded_geo_locations` is the usual case: the "Urban" level excludes
 * the rural regions, the "Rural" level excludes nothing, and Meta stores
 * nothing for it. That absence is the level's real targeting, not an
 * authoring mistake, so the level should copy what it has and omit the
 * rest. A property that *no* level carries is a different thing -- the
 * variable is asking for data none of its adsets have -- and stays an
 * error. The caller passes this list as `extractFromAdset`'s `optional`.
 *
 * A level whose adset is not in `adsets` contributes nothing here; it
 * reports `AdsetNotFoundError` on its own.
 */
export const propertiesOnSomeLevel = (
  levels: Array<{ template_adset?: string }>,
  adsets: any[],
  properties: string[]
): string[] => {
  const targetings = (levels || [])
    .map(
      level =>
        (adsets || []).find((a: any) => a.id === level.template_adset)
          ?.targeting
    )
    .filter(t => t && typeof t === 'object');
  return (properties || []).filter(p => targetings.some(t => p in t));
};

/**
 * The keys a level's stored targeting should carry: `properties`, minus
 * those `wouldApply` legitimately left out because this level's adset lacks
 * them. Feed this to `diffPropertyKeys` rather than the raw `properties`, or
 * a level that correctly omits an optional key reads as permanently
 * "added" and out of sync.
 */
export const expectedPropertyKeys = (
  wouldApply: any,
  properties: string[]
): string[] => {
  if (!wouldApply || typeof wouldApply !== 'object') return properties || [];
  return (properties || []).filter(p => p in wouldApply);
};

const stripTargetingAutomation = (obj: any): any => {
  if (!obj || typeof obj !== 'object') return {};
  const clone = { ...obj };
  delete clone.targeting_automation;
  return clone;
};

/**
 * True iff `stored` and `wouldApply` are the same targeting minus the
 * always-emitted `targeting_automation` block. Used by the level UI to
 * detect drift between what the user has saved and what Apply would
 * write right now.
 *
 * Comparison goes through lodash `isEqual`, not `JSON.stringify`, because
 * a fresh Apply builds keys in `variable.properties` order while the
 * saved blob may have a different order — the two are otherwise equivalent
 * but stringify comparison would treat them as out of sync.
 */
export const isLevelInSync = (stored: any, wouldApply: any): boolean => {
  return isEqual(
    stripTargetingAutomation(stored),
    stripTargetingAutomation(wouldApply)
  );
};

/**
 * Diff the set of property keys that produced `stored` against the
 * variable's currently-selected `current` properties. Treats
 * `targeting_automation` as engine noise, not a user choice. The
 * returned `keysDiffer` is what triggers the level's two-line banner;
 * when only values drift, the level renders the one-line banner instead.
 */
export const diffPropertyKeys = (
  stored: any,
  current: string[]
): { added: string[]; removed: string[]; keysDiffer: boolean } => {
  const storedKeys = (
    stored && typeof stored === 'object' ? Object.keys(stored) : []
  ).filter(k => k !== 'targeting_automation');
  const sortedStored = [...storedKeys].sort().join('|');
  const sortedCurrent = [...(current || [])].sort().join('|');
  const keysDiffer = sortedStored !== sortedCurrent;
  const added = (current || []).filter(k => !storedKeys.includes(k));
  const removed = storedKeys.filter(k => !(current || []).includes(k));
  return { added, removed, keysDiffer };
};
