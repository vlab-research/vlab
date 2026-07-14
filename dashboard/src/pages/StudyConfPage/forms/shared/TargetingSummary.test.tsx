/* eslint-disable testing-library/render-result-naming-convention */
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { renderTargetingSummary } from './TargetingSummary';

const getSummaryText = (targeting: any): string => {
  return renderToStaticMarkup(renderTargetingSummary(targeting));
};

describe('renderTargetingSummary', () => {
  it('renders empty state when targeting is empty', () => {
    expect(getSummaryText({})).toContain('No targeting data');
    expect(getSummaryText(null)).toContain('No targeting data');
    expect(getSummaryText(undefined)).toContain('No targeting data');
  });

  it('renders only geo locations with countries', () => {
    const summary = getSummaryText({
      geo_locations: { countries: ['US', 'NG'], location_types: ['home'] },
    });
    expect(summary).toContain('Geo:');
    expect(summary).toContain('2 countries');
    expect(summary).toContain('types: home');
  });

  it('renders geo locations with cities, regions, and custom locations', () => {
    const summary = getSummaryText({
      geo_locations: {
        cities: [{ key: 'NG-BA', name: 'Bauchi' }, { key: 'NG-LA', name: 'Lagos' }],
        regions: [{ key: 'NG-LAGOS', name: 'Lagos State' }],
        custom_locations: [{ name: 'Headquarters', latitude: 6.5, longitude: 3.4 }],
      },
    });
    expect(summary).toContain('Geo:');
    expect(summary).toContain('Bauchi');
    expect(summary).toContain('Lagos State');
    expect(summary).toContain('Headquarters');
  });

  it('renders excluded geo locations separately', () => {
    const summary = getSummaryText({
      excluded_geo_locations: { countries: ['CD'] },
    });
    expect(summary).toContain('Excluded Geo:');
    expect(summary).toContain('1 country');
  });

  it('renders age and gender', () => {
    const summary = getSummaryText({ age_min: 18, age_max: 34, genders: [1, 2] });
    expect(summary).toContain('Age: 18–34');
    expect(summary).toContain('Gender: Male, Female');
  });

  it('renders custom audiences', () => {
    const summary = getSummaryText({
      custom_audiences: [{ id: 'aud1', name: 'Lookalike' }],
      excluded_custom_audiences: [{ id: 'aud2', name: 'Exclude list' }],
    });
    expect(summary).toContain('Audiences: Lookalike');
    expect(summary).toContain('Excluded Audiences: Exclude list');
  });

  it('renders flexible spec contents', () => {
    const summary = getSummaryText({
      flexible_spec: [
        { interests: [{ id: '1', name: 'Running' }, { id: '2', name: 'Cycling' }] },
        { behaviors: [{ id: '3', name: 'Frequent travelers' }] },
      ],
    });
    expect(summary).toContain('Flexible:');
    expect(summary).toContain('Interests: Running, Cycling');
    expect(summary).toContain('[2] Behaviors: Frequent travelers');
  });

  it('renders exclusions contents', () => {
    const summary = getSummaryText({
      exclusions: { interests: [{ id: '4', name: 'Gaming' }] },
    });
    expect(summary).toContain('Exclusions:');
    expect(summary).toContain('Interests: Gaming');
  });

  it('lists unknown keys when no known properties are present', () => {
    const summary = getSummaryText({ publisher_platforms: ['facebook', 'instagram'] });
    expect(summary).toContain('publisher_platforms');
  });

  it('does not render an Advantage+ Audience line', () => {
    const summary = getSummaryText({
      age_min: 18,
      targeting_automation: { advantage_audience: 0 },
    });
    expect(summary).not.toContain('Advantage+');
  });

  it('does not list targeting_automation as an unknown key', () => {
    const summary = getSummaryText({
      publisher_platforms: ['facebook'],
      targeting_automation: { advantage_audience: 0 },
    });
    expect(summary).toContain('publisher_platforms');
    expect(summary).not.toContain('targeting_automation');
  });

  it('renders many geo values with an ellipsis', () => {
    const cities = Array.from({ length: 5 }, (_, i) => ({ key: `city-${i}`, name: `City ${i}` }));
    const summary = getSummaryText({ geo_locations: { cities } });
    expect(summary).toContain('+2 more');
  });
});
