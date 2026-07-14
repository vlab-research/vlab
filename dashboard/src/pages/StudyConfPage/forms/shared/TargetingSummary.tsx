import React from 'react';

const GENDER_LABELS: Record<string | number, string> = {
  1: 'Male',
  2: 'Female',
  0: 'All',
};

const TARGETING_CATEGORY_LABELS: Record<string, string> = {
  interests: 'Interests',
  behaviors: 'Behaviors',
  life_events: 'Life Events',
  education_majors: 'Majors',
  education_schools: 'Schools',
  work_employers: 'Employers',
  work_job_titles: 'Job Titles',
  family_statuses: 'Family',
  relationship_statuses: 'Relationship',
  politics: 'Politics',
  industries: 'Industries',
  fields_of_study: 'Fields of Study',
  demographics: 'Demographics',
  user_adclusters: 'Ad Clusters',
  custom_audiences: 'Audiences',
  excluded_custom_audiences: 'Excluded Audiences',
  geo_locations: 'Locations',
  excluded_geo_locations: 'Excluded Locations',
  education_statuses: 'Education',
  locale: 'Locale',
  user_device: 'Devices',
  user_os: 'OS',
  wireless: 'Wireless',
  work_positions: 'Positions',
  cohort_specs: 'Cohorts',
};

const RENDERED_TARGETING_KEYS = new Set([
  'geo_locations',
  'excluded_geo_locations',
  'age_min',
  'age_max',
  'genders',
  'custom_audiences',
  'excluded_custom_audiences',
  'flexible_spec',
  'exclusions',
  'targeting_automation',
]);

const joinWithEllipsis = (items: string[], limit = 3): string => {
  const shown = items.slice(0, limit);
  const rest = items.length - limit;
  if (rest > 0) {
    return `${shown.join(', ')} +${rest} more`;
  }
  return shown.join(', ');
};

const formatTargetingItems = (items: any[]): string => {
  if (!Array.isArray(items) || items.length === 0) {
    return '';
  }
  const names = items
    .map(item => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        return item.name || item.description || item.key || item.id || '';
      }
      return String(item);
    })
    .filter(Boolean);
  return joinWithEllipsis(names);
};

const formatCategoryEntries = (obj: any): string => {
  if (!obj || typeof obj !== 'object') return '';
  return Object.entries(obj)
    .map(([key, values]) => {
      const label = TARGETING_CATEGORY_LABELS[key] || key;
      const summary = formatTargetingItems(values as any[]);
      return summary ? `${label}: ${summary}` : '';
    })
    .filter(Boolean)
    .join(', ');
};

const summarizeGeoLocations = (geo: any): string => {
  if (!geo || typeof geo !== 'object') {
    return '';
  }

  const segments: string[] = [];

  if (geo.countries?.length) {
    const count = geo.countries.length;
    segments.push(`${count} countr${count === 1 ? 'y' : 'ies'}`);
  }

  if (geo.regions?.length) {
    const names = geo.regions
      .map((r: any) => r.name || r.key || '')
      .filter(Boolean);
    segments.push(joinWithEllipsis(names));
  }

  if (geo.cities?.length) {
    const names = geo.cities
      .map((c: any) => c.name || c.key || '')
      .filter(Boolean);
    segments.push(joinWithEllipsis(names));
  }

  if (geo.custom_locations?.length) {
    const names = geo.custom_locations
      .map((l: any) => l.name || (l.latitude != null && l.longitude != null ? `${l.latitude},${l.longitude}` : '') || '')
      .filter(Boolean);
    segments.push(joinWithEllipsis(names));
  }

  if (geo.zips?.length) {
    const names = geo.zips
      .map((z: any) => z.key || '')
      .filter(Boolean);
    segments.push(joinWithEllipsis(names));
  }

  if (geo.places?.length) {
    const names = geo.places
      .map((p: any) => p.name || p.key || '')
      .filter(Boolean);
    segments.push(joinWithEllipsis(names));
  }

  if (geo.location_types?.length) {
    segments.push(`types: ${geo.location_types.join(', ')}`);
  }

  return segments.join(' · ');
};

const summarizeFlexibleSpec = (flex: any): string => {
  if (!Array.isArray(flex) || flex.length === 0) {
    return '';
  }

  const bucketSummaries = flex
    .map((bucket, index) => {
      const summary = formatCategoryEntries(bucket);
      if (!summary) return '';
      return flex.length > 1 ? `[${index + 1}] ${summary}` : summary;
    })
    .filter(Boolean);

  return bucketSummaries.join(' · ');
};

/**
 * Pure renderer for facebook_targeting objects.
 * Used by both Level.tsx (variables) and Stratum.tsx (strata) for visual consistency.
 *
 * Surfaces the content that actually varies between strata: geolocation,
 * age/gender, custom audiences, and flexible spec details. Avoids highlighting
 * Advantage+ Audience because the extraction pipeline always disables it; that
 * policy is now an implementation detail rather than a prominent summary line.
 *
 * Returns a readable summary of the targeting data; unknown top-level keys are
 * listed at the end so they are still discoverable without burying useful data.
 */
export const renderTargetingSummary = (targeting: any) => {
  if (!targeting || Object.keys(targeting).length === 0) {
    return <span className="text-gray-400 italic">No targeting data</span>;
  }

  const parts: string[] = [];

  const geoSummary = summarizeGeoLocations(targeting.geo_locations);
  if (geoSummary) {
    parts.push(`Geo: ${geoSummary}`);
  }

  const excludedGeoSummary = summarizeGeoLocations(targeting.excluded_geo_locations);
  if (excludedGeoSummary) {
    parts.push(`Excluded Geo: ${excludedGeoSummary}`);
  }

  if (targeting.age_min != null || targeting.age_max != null) {
    const minAge = targeting.age_min ?? '18';
    const maxAge = targeting.age_max ?? '65+';
    parts.push(`Age: ${minAge}–${maxAge}`);
  }

  if (targeting.genders) {
    const genders = (targeting.genders || [])
      .map((g: any) => GENDER_LABELS[g] || String(g))
      .join(', ');
    if (genders) parts.push(`Gender: ${genders}`);
  }

  if (targeting.custom_audiences) {
    const auds = formatTargetingItems(targeting.custom_audiences);
    if (auds) parts.push(`Audiences: ${auds}`);
  }

  if (targeting.excluded_custom_audiences) {
    const auds = formatTargetingItems(targeting.excluded_custom_audiences);
    if (auds) parts.push(`Excluded Audiences: ${auds}`);
  }

  const flexSummary = summarizeFlexibleSpec(targeting.flexible_spec);
  if (flexSummary) {
    parts.push(`Flexible: ${flexSummary}`);
  }

  if (targeting.exclusions) {
    const exclusionSummary = Array.isArray(targeting.exclusions)
      ? summarizeFlexibleSpec(targeting.exclusions)
      : formatCategoryEntries(targeting.exclusions);
    if (exclusionSummary) {
      parts.push(`Exclusions: ${exclusionSummary}`);
    }
  }

  const unknownKeys = Object.keys(targeting).filter(k => !RENDERED_TARGETING_KEYS.has(k));

  if (parts.length === 0) {
    if (unknownKeys.length === 0) {
      return <span className="text-gray-400 italic">No targeting data</span>;
    }
    return <div className="text-sm text-gray-600">{unknownKeys.join(', ')}</div>;
  }

  return (
    <div className="text-sm space-y-1">
      {parts.map((p, i) => <div key={i}>{p}</div>)}
      {unknownKeys.length > 0 && (
        <div className="text-xs text-gray-500">Other: {unknownKeys.join(', ')}</div>
      )}
    </div>
  );
};
