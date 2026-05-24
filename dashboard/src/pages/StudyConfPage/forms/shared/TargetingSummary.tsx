import React from 'react';

/**
 * Pure renderer for facebook_targeting objects.
 * Used by both Level.tsx (variables) and Stratum.tsx (strata) for visual consistency.
 * Returns a readable summary of the targeting data; falls back to key names for unknown properties.
 */
export const renderTargetingSummary = (targeting: any) => {
  if (!targeting || Object.keys(targeting).length === 0) {
    return <span className="text-gray-400 italic">No targeting data</span>;
  }

  const parts: string[] = [];

  if (targeting.geo_locations?.cities) {
    const cities = targeting.geo_locations.cities.slice(0, 3).map((c: any) => c.name || c.key);
    parts.push(`Locations: ${cities.join(', ')}`);
  }

  if (targeting.age_min || targeting.age_max) {
    const minAge = targeting.age_min || '18';
    const maxAge = targeting.age_max || '65+';
    parts.push(`Age: ${minAge}–${maxAge}`);
  }

  if (targeting.genders) {
    const genderMap: Record<number, string> = { 1: 'M', 2: 'F' };
    const genders = (targeting.genders || []).map((g: number) => genderMap[g] || g).join(', ');
    if (genders) parts.push(`Gender: ${genders}`);
  }

  if (targeting.custom_audiences) {
    const audNames = targeting.custom_audiences.slice(0, 2).map((a: any) => a.name || a.id);
    parts.push(`Audiences: ${audNames.join(', ')}`);
  }

  if (parts.length === 0) {
    // Fallback: list keys we don't have pretty renderers for
    const keys = Object.keys(targeting).filter(k => k !== 'targeting_automation');
    return <span className="text-gray-600 text-sm">{keys.join(', ')}</span>;
  }

  return <div className="text-sm space-y-1">{parts.map((p, i) => <div key={i}>{p}</div>)}</div>;
};
