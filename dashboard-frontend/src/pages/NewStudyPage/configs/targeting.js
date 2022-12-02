export const targeting = {
  type: 'config-object',
  title: 'Targeting',
  description:
    'Targeting describes the variables for stratification and the desired joint distribution of respondents.',
  fields: [
    {
      name: 'template_campaign_name',
      type: 'text',
      label: 'Template campaign name',
      helperText:
        'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
    },
    {
      name: 'distribution_vars',
      type: 'select',
      label: 'Distribution variables',
      defaultValue: 'Select a distribution variable',
      options: [
        {
          name: 'location',
          label: 'Location',
        },
        {
          name: 'gender',
          label: 'Gender',
        },
        {
          name: 'age',
          label: 'Age',
        },
      ],
    },
  ],
};
