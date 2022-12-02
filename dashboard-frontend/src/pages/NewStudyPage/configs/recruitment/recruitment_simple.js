export const recruitment_simple = {
  type: 'config-object',
  title: 'Recruitment simple',
  description: 'Simple recruitment...',
  fields: [
    {
      name: 'ad_campaign_name',
      type: 'text',
      label: 'Ad campaign name',
      helperText: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget',
      type: 'number',
      label: 'Budget',
      helperText: 'E.g 8400',
    },
    {
      name: 'max_sample',
      type: 'number',
      label: 'Maximum sample',
      helperText: 'E.g 1000',
    },
    {
      name: 'start_date',
      type: 'text',
      label: 'Start date',
      helperText: 'E.g 2022-01-10',
    },
    {
      name: 'end_date',
      type: 'text',
      label: 'End date',
      helperText: 'E.g 2022-01-31',
    },
  ],
};
