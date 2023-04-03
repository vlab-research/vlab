import Select from './../src/pages/NewStudyPage/components/form/inputs/Select';
import Text from './../src/pages/NewStudyPage/components/form/inputs/Text';

const state = [
  {
    create_study: [
      {
        id: 'name',
        name: 'name',
        type: 'text',
        component: Text,
        label: 'Give your study a name',
        helper_text: 'E.g example-fly-conf',
        options: undefined,
        value: '',
      },
    ],
    general: [
      {
        id: 'objective',
        name: 'objective',
        type: 'select',
        component: Select,
        label: 'Objective',
        helper_text: undefined,
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
        value: 'default',
      },
      {
        id: 'optimization_goal',
        name: 'optimization_goal',
        type: 'select',
        component: Select,
        label: 'Optimization goal',
        helper_text: undefined,
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
        value: 'default',
      },
      {
        id: 'destination_type',
        name: 'destination_type',
        type: 'select',
        component: Select,
        label: 'Destination type',
        helper_text: undefined,
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
        value: 'default',
      },
      {
        id: 'page_id',
        name: 'page_id',
        type: 'text',
        component: Text,
        label: 'Page Id',
        helper_text: 'E.g 1855355231229529',
        options: undefined,
        value: '',
      },
      {
        id: 'min_budget',
        name: 'min_budget',
        type: 'number',
        component: Text,
        label: 'Minimum budget',
        helper_text: 'E.g 10',
        options: undefined,
        value: 1,
      },
      {
        id: 'opt_window',
        name: 'opt_window',
        type: 'number',
        component: Text,
        label: 'Opt window',
        helper_text: 'E.g 48',
        options: undefined,
        value: 1,
      },
      {
        id: 'instagram_id',
        name: 'instagram_id',
        type: 'text',
        component: Text,
        label: 'Instagram Id',
        helper_text: 'E.g 2327764173962588',
        options: undefined,
        value: '',
      },
      {
        id: 'ad_account',
        name: 'ad_account',
        type: 'text',
        component: Text,
        label: 'Ad account',
        helper_text: 'E.g 1342820622846299',
        options: undefined,
        value: '',
      },
    ],
  },
];

export default state;
