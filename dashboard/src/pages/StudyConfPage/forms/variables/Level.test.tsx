import React from 'react';
import { render, screen } from '@testing-library/react';
import Level from './Level';
import { propertiesOnSomeLevel } from './extract';

// A geographic variable as Meta actually stores it: the urban ad set
// excludes the rural regions, the rural one excludes nothing, so Meta writes
// no `excluded_geo_locations` key on it at all. The rural level must read as
// fine, not as an error, because that absence is its real targeting.
const urban = {
  id: 'adset-urban',
  name: 'Argentina - Urban',
  targeting: {
    geo_locations: { regions: [{ key: '1', name: 'Buenos Aires' }] },
    excluded_geo_locations: { regions: [{ key: '2', name: 'Pampa' }] },
  },
};
const rural = {
  id: 'adset-rural',
  name: 'Argentina - Rural',
  targeting: { geo_locations: { regions: [{ key: '2', name: 'Pampa' }] } },
};
const adsets = [urban, rural];
const levels = [
  { template_adset: 'adset-urban' },
  { template_adset: 'adset-rural' },
];

const renderRural = (properties: string[], facebook_targeting: any) =>
  render(
    <Level
      data={{
        name: 'Rural',
        template_adset: 'adset-rural',
        quota: 0,
        facebook_targeting,
      }}
      index={1}
      adsets={adsets}
      update={jest.fn()}
      properties={properties}
      optionalProperties={propertiesOnSomeLevel(levels, adsets, properties)}
    />
  );

describe('a level whose adset lacks a property another level has', () => {
  const properties = ['geo_locations', 'excluded_geo_locations'];

  it('shows no error', () => {
    renderRural(properties, {});

    expect(screen.queryByTestId('level-error')).toBeNull();
  });

  it('is in sync once its stored targeting omits the property too', () => {
    renderRural(properties, {
      geo_locations: { regions: [{ key: '2', name: 'Pampa' }] },
      targeting_automation: { advantage_audience: 0 },
    });

    expect(screen.queryByTestId('level-error')).toBeNull();
    expect(screen.queryByTestId('level-out-of-sync-banner')).toBeNull();
  });
});

describe('a level whose adset lacks a property no level has', () => {
  it('names the adset and the property, and says no other level has it', () => {
    renderRural(['geo_locations', 'custom_audiences'], {});

    const banner = screen.getByTestId('level-error');
    expect(banner).toHaveTextContent('Argentina - Rural');
    expect(banner).toHaveTextContent('custom_audiences');
    expect(banner).toHaveTextContent(/neither does any other level/i);
  });
});
