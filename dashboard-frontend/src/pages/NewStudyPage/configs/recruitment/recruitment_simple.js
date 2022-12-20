export const recruitment_simple = {
  type: 'config-object',
  title: 'Recruitment simple',
  description: 'Simple recruitment...',
  fields: [
    {
      name: 'ad_campaign_name',
      type: 'text',
      label: 'Ad campaign name',
      helpertext: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget',
      type: 'number',
      label: 'Budget',
      helpertext: 'E.g 8400',
    },
    {
      name: 'max_sample',
      type: 'number',
      label: 'Maximum sample',
      helpertext: 'E.g 1000',
    },
    {
      name: 'start_date',
      type: 'text',
      label: 'Start date',
      helpertext: 'E.g 2022-01-10',
    },
    {
      name: 'end_date',
      type: 'text',
      label: 'End date',
      helpertext: 'E.g 2022-01-31',
    },
  ],
};
