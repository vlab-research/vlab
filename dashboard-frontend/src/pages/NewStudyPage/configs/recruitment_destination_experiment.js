export const recruitment_destination_experiment = {
  configType: 'recruitment_destination_experiment',
  description:
    ' Use this when you want to create a multi-arm randomized experiment (A/B test on Facebook) where some of your sample is sent to different "destinations".',
  fields: [
    {
      name: 'ad_campaign_name_base',
      type: 'text',
      label: 'Ad campaign name base',
      helpertext: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget_per_arm',
      type: 'text',
      label: 'Budget per arm',
      helpertext: 'E.g 8400',
    },
    {
      name: 'max_sample_per_arm',
      type: 'text',
      label: 'Maximum sample per arm',
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
    {
      name: 'destinations',
      type: 'select',
      label: 'Destinations',
      options: [
        {
          name: 'Lottery',
        },
        {
          name: 'Top-up',
        },
      ],
    },
  ],
};
