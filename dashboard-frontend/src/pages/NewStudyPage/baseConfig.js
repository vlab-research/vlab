import countries from '../../fixtures/countries.json';

export const baseConfig = [
  {
    name: 'name',
    type: 'text',
    label: 'Name',
  },
  {
    name: 'objective',
    type: 'select',
    label: 'Objective',
    options: [
      {
        name: 'objective 1',
      },
      {
        name: 'objective 2',
      },
      {
        name: 'objective 3',
      },
    ],
  },
  {
    name: 'optimization_goal',
    type: 'select',
    label: 'Optimization Goal',
    options: [
      {
        name: 'optimization goal 1',
      },
      {
        name: 'optimization goal 2',
      },
      {
        name: 'optimization goal 3',
      },
    ],
  },
  {
    name: 'destination_type',
    type: 'select',
    label: 'Destination Type',
    options: [
      {
        name: 'destination type 1',
      },
      {
        name: 'destination type 2',
      },
      {
        name: 'destination type 3',
      },
    ],
  },
  {
    name: 'page_id',
    type: 'text',
    label: 'Page ID',
  },
  {
    name: 'min_budget',
    type: 'text',
    label: 'Minimum Budget',
  },
  {
    name: 'opt_window',
    type: 'text',
    label: 'Opt-in Window',
  },
  {
    name: 'instagram_id',
    type: 'text',
    label: 'Instagram ID',
  },
  {
    name: 'ad_account',
    type: 'text',
    label: 'Ad Account',
  },
  {
    name: 'country',
    type: 'select',
    label: 'Country',
    options: countries,
  },
];
