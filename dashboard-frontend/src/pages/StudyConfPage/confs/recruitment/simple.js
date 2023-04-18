const simple = {
  type: 'confObject',
  title: 'Recruitment simple',
  description: 'Simple recruitment...',
  fields: [
    {
      name: 'ad_campaign_name',
      type: 'text',
      label: 'Ad campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget',
      type: 'number',
      label: 'Budget',
      helper_text: 'E.g 8400',
    },
    {
      name: 'max_sample',
      type: 'number',
      label: 'Maximum sample',
      helper_text: 'E.g 1000',
    },
    {
      name: 'start_date',
      type: 'text',
      label: 'Start date',
      helper_text: 'E.g 2022-01-10',
    },
    {
      name: 'end_date',
      type: 'text',
      label: 'End date',
      helper_text: 'E.g 2022-01-31',
    },
  ],
};

export default simple;
