export const recruitment_pipeline_experiment = {
  configType: 'recruitment_pipeline_experiment',
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
    {
      name: 'arms',
      type: 'text',
      label: 'Arms',
      helpertext: 'E.g 2',
    },
    {
      name: 'recruitment_days',
      type: 'text',
      label: 'Recruitment Days',
      helpertext: 'E.g 10',
    },
    {
      name: 'offset_days',
      type: 'text',
      label: 'Offset Days',
      helpertext: 'E.g 20',
    },
  ],
};
