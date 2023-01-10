export const recruitment_pipeline_experiment = {
  type: 'configObject',
  title: 'Recruitment pipeline',
  description:
    'In this design, we generate an A/B test on Facebook but instead of sending your sample to different destinations, we run the ads at different times (a pipeline experiment design). You can set up how long each arm runs, and how long they are offset from the start of the previous arm.',
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
    //   label: 'Saved destinations',
    //   options: mapDestinations(destinations), // TODO change this to a call to action prop?
    // },
    {
      name: 'arms',
      type: 'number',
      label: 'Arms',
      helper_text: 'E.g 2',
    },
    {
      name: 'recruitment_days',
      type: 'number',
      label: 'Recruitment Days',
      helper_text: 'E.g 10',
    },
    {
      name: 'offset_days',
      type: 'number',
      label: 'Offset Days',
      helper_text: 'E.g 20',
    },
  ],
};
