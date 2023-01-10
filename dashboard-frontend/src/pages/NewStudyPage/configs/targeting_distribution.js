import countries from '../../../fixtures/countries';

export const targeting_distribution = {
  type: 'configObject',
  title: 'Targeting distribution',
  description:
    'What proportion of people do you want in your final sample from each stratum?',
  fields: [
    {
      name: 'age',
      type: 'text',
      label: 'Age',
      helper_text: 'E.g 18',
    },
    {
      name: 'gender',
      type: 'text',
      label: 'Gender',
      helper_text: 'E.g 1',
    },
    {
      name: 'location',
      type: 'select',
      label: 'Location',
      defaultValue: 'Select a country',
      options: countries,
    },
  ],
};
