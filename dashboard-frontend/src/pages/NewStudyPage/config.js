import { translator } from '../../helpers/translator';
import countries from '../../fixtures/countries.json';

const config = [
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
    name: 'optimizationGoal',
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
    name: 'destinationType',
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
    name: 'minBudget',
    type: 'text',
    label: 'Minimum Budget',
  },
  {
    name: 'instagramId',
    type: 'text',
    label: 'Instagram ID',
  },
  {
    name: 'adAccount',
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

export const getConfig = () => {
  return config.map(translator);
};
