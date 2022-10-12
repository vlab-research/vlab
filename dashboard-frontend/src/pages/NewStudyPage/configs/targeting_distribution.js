import countries from '../../../fixtures/countries.json';

export const targeting_distribution = {
  configType: 'targeting_distribution',
  description:
    'What proportion of people do you want in your final sample from each stratum?',
  fields: [
    {
      name: 'age',
      type: 'text',
      label: 'Age',
      helpertext: 'E.g 18',
    },
    {
      name: 'gender',
      type: 'text',
      label: 'Gender',
      helpertext: 'E.g 1',
    },
    {
      name: 'location',
      type: 'select',
      label: 'Location',
      options: countries,
    },
  ],
};
