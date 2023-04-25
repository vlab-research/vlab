const formData = {
  create_study: {
    name: 'foo',
  },
  general: {
    objective: 'reach',
    optimization_goal: 'social_impressions',
    destination_type: 'app',
    page_id: '12345',
    min_budget: 1,
    opt_window: 1,
    instagram_id: '54321',
    ad_account: '111111',
  },
  recruitment: {
    recruitment_type: 'recruitment_simple',
    ad_campaign_name: 'vlab-most-used-prog-1',
    budget: 10000,
    max_sample: 1000,
    start_date: '2022-07-26T00:00:00',
    end_date: '2022-08-05T00:00:00',
  },
  destinations: [
    {
      name: 'fly',
      initial_shortcode: '12345',
    },
    {
      name: 'typeform',
      url_template: 'typeform/some-url',
    },
  ],
  simple_list: ['foobar', 'foobaz', 'foobazzle'],
};

export default formData;
