/**
 * Pure extraction module for facebook_targeting from template adsets.
 * Typed error handling allows the UI to render specific, actionable messages.
 * No React dependencies; testable in isolation.
 */

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
 * @returns Object with extracted targeting properties
 * @throws AdsetNotFoundError if adset is null or undefined
 * @throws PropertyMissingError if any requested property is not present on the adset
 */
export function extractFromAdset(
  adset: any | null | undefined,
  properties: string[]
): any {
  if (!adset) {
    throw new AdsetNotFoundError('(unknown)');
  }

  const extracted: any = {};

  for (const property of properties) {
    if (!(property in adset.targeting)) {
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
 */
export const isLevelInSync = (stored: any, wouldApply: any): boolean => {
  return JSON.stringify(stripTargetingAutomation(stored)) ===
    JSON.stringify(stripTargetingAutomation(wouldApply));
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
  current: string[],
): { added: string[]; removed: string[]; keysDiffer: boolean } => {
  const storedKeys = (stored && typeof stored === 'object'
    ? Object.keys(stored)
    : []
  ).filter(k => k !== 'targeting_automation');
  const sortedStored = [...storedKeys].sort().join('|');
  const sortedCurrent = [...(current || [])].sort().join('|');
  const keysDiffer = sortedStored !== sortedCurrent;
  const added = (current || []).filter(k => !storedKeys.includes(k));
  const removed = storedKeys.filter(k => !(current || []).includes(k));
  return { added, removed, keysDiffer };
};
