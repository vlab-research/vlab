export const general = {
  type: 'confObject',
  title: 'General',
  description: 'The "general" configuration consists of... General stuff?',
  fields: [
    {
      name: 'objective',
      type: 'select',
      label: 'Objective',
      options: [
        {
          name: 'default',
          label: 'Select an objective',
        },
        {
          name: 'app_installs',
          label: 'App installs',
        },
        {
          name: 'brand_awareness',
          label: 'Brand awareness',
        },
        {
          name: 'conversions',
          label: 'Conversions',
        },
        {
          name: 'event_responses',
          label: 'Event responses',
        },
        {
          name: 'lead_generation',
          label: 'Lead generation',
        },
        {
          name: 'link_clicks',
          label: 'Link clicks',
        },
        {
          name: 'local_awareness',
          label: 'Local awareness',
        },
        {
          name: 'messages',
          label: 'Messages',
        },
        {
          name: 'offer_claims',
          label: 'Offer claims',
        },
        {
          name: 'page_likes',
          label: 'Page likes',
        },
        {
          name: 'post_engagement',
          label: 'Post engagement',
        },
        {
          name: 'product_catalog_sales',
          label: 'Product catalog sales',
        },
        {
          name: 'reach',
          label: 'Reach',
        },
        {
          name: 'store_visits',
          label: 'Store visits',
        },
      ],
    },
    {
      name: 'optimization_goal',
      type: 'select',
      label: 'Optimization goal',
      options: [
        {
          name: 'default',
          label: 'Select an optimization goal',
        },
        {
          name: 'ad_recall_lift',
          label: 'Ad recall lift',
        },
        {
          name: 'app_downloads',
          label: 'App downloads',
        },
        {
          name: 'app_installs',
          label: 'App installs',
        },
        {
          name: 'brand_awareness',
          label: 'Brand awareness',
        },
        {
          name: 'clicks',
          label: 'Clicks',
        },
        {
          name: 'derived_events',
          label: 'Derived events',
        },
        {
          name: 'engaged_users',
          label: 'Engaged users',
        },
        {
          name: 'event_responses',
          label: 'Event responses',
        },
        {
          name: 'impressions',
          label: 'Impressions',
        },
        {
          name: 'landing_page_views',
          label: 'Landing page views',
        },
        {
          name: 'lead_generation',
          label: 'Lead generation',
        },
        {
          name: 'link_clicks',
          label: 'Link clicks',
        },
        {
          name: 'none',
          label: 'None',
        },
        {
          name: 'offer_claims',
          label: 'Offer claims',
        },
        {
          name: 'offsite_conversions',
          label: 'Offsite conversions',
        },
        {
          name: 'page_engagement',
          label: 'Page engagement',
        },
        {
          name: 'page_likes',
          label: 'Page likes',
        },
        {
          name: 'post_engagement',
          label: 'Post engagement',
        },
        {
          name: 'reach',
          label: 'Reach',
        },
        {
          name: 'replies',
          label: 'Replies',
        },
        {
          name: 'replies',
          label: 'Replies',
        },
        {
          name: 'social_impressions',
          label: 'Social impressions',
        },
        {
          name: 'thruplay',
          label: 'Thruplay',
        },
        {
          name: 'two_second_continuous_video_views',
          label: 'Two second continuous video views',
        },
        {
          name: 'visit_instagram_profile',
          label: 'Visit instagram profile',
        },
      ],
    },
    {
      name: 'destination_type',
      type: 'select',
      label: 'Destination type',
      defaultValue: 'Select a destination type',
      options: [
        {
          name: 'default',
          label: 'Select a destination type',
        },
        {
          name: 'web',
          label: 'Web',
        },
        {
          name: 'messenger',
          label: 'Messenger',
        },
        {
          name: 'app',
          label: 'App',
        },
      ],
    },
    {
      name: 'page_id',
      type: 'text',
      label: 'Page Id',
      helper_text: 'E.g 1855355231229529',
    },
    {
      name: 'min_budget',
      type: 'number',
      label: 'Minimum budget',
      helper_text: 'E.g 10',
    },
    {
      name: 'opt_window',
      type: 'number',
      label: 'Opt window',
      helper_text: 'E.g 48',
    },
    {
      name: 'instagram_id',
      type: 'text',
      label: 'Instagram Id',
      helper_text: 'E.g 2327764173962588',
    },
    {
      name: 'ad_account',
      type: 'text',
      label: 'Ad account',
      helper_text: 'E.g 1342820622846299',
    },
  ],
};
