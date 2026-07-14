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

  // Always include targeting_automation if present, regardless of properties selection.
  if (adset.targeting.targeting_automation !== undefined) {
    extracted.targeting_automation = adset.targeting.targeting_automation;
  }

  return extracted;
}
