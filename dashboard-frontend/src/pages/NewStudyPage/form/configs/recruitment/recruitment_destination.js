export const recruitment_destination = {
  type: 'configObject',
  title: 'Recruitment destination',
  description:
    ' Use this when you want to create a multi-arm randomized experiment (A/B test on Facebook) where some of your sample is sent to different "destinations".',
  fields: [
    {
      name: 'ad_campaign_name_base',
      type: 'text',
      label: 'Ad campaign name base',
      helper_text: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget_per_arm',
      type: 'number',
      label: 'Budget per arm',
      helper_text: 'E.g 8400',
    },
    {
      name: 'max_sample_per_arm',
      type: 'number',
      label: 'Maximum sample per arm',
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
    // {
    //   name: 'destinations',
    //   type: 'list',
    //   label: 'Add new destination',
    //   options: mapDestinations(destinations),
    // },
  ],
};
