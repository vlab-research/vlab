import Select from '../../src/pages/NewStudyPage/components/form/inputs/Select';
import Text from '../../src/pages/NewStudyPage/components/form/inputs/Text';
import Button from '../../src/pages/NewStudyPage/components/form/inputs/Button';
import Fieldset from '../../src/pages/NewStudyPage/components/form/Fieldset';
import app from '../../src/pages/StudyConfPage/confs/destinations/app';
import messenger from '../../src/pages/StudyConfPage/confs/destinations/messenger';
import web from '../../src/pages/StudyConfPage/confs/destinations/web';

const initialState = [
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
        conf: undefined,
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
        value: 'app_installs',
        conf: undefined,
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
        value: 'ad_recall_lift',
        conf: undefined,
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
        value: 'web',
        conf: undefined,
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
        conf: undefined,
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
        conf: undefined,
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
        conf: undefined,
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
        conf: undefined,
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
        conf: undefined,
      },
    ],
    recruitment: [
      {
        id: 'recruitment_type',
        name: 'recruitment_type',
        type: 'select',
        component: Select,
        label: 'Select a recruitment type',
        helper_text: undefined,
        options: [
          { name: 'recruitment_simple', label: 'Recruitment simple' },
          { name: 'recruitment_pipeline', label: 'Recruitment pipeline' },
          { name: 'recruitment_destination', label: 'Recruitment destination' },
        ],
        value: 'recruitment_simple',
        conf: undefined,
      },
      {
        id: 'ad_campaign_name',
        name: 'ad_campaign_name',
        type: 'text',
        component: Text,
        label: 'Ad campaign name',
        helper_text: 'E.g vlab-vaping-pilot-2',
        options: undefined,
        value: '',
        conf: undefined,
      },
      {
        id: 'budget',
        name: 'budget',
        type: 'number',
        component: Text,
        label: 'Budget',
        helper_text: 'E.g 8400',
        options: undefined,
        value: 1,
        conf: undefined,
      },
      {
        id: 'max_sample',
        name: 'max_sample',
        type: 'number',
        component: Text,
        label: 'Maximum sample',
        helper_text: 'E.g 1000',
        options: undefined,
        value: 1,
        conf: undefined,
      },
      {
        id: 'start_date',
        name: 'start_date',
        type: 'text',
        component: Text,
        label: 'Start date',
        helper_text: 'E.g 2022-01-10',
        options: undefined,
        value: '',
        conf: undefined,
      },
      {
        id: 'end_date',
        name: 'end_date',
        type: 'text',
        component: Text,
        label: 'End date',
        helper_text: 'E.g 2022-01-31',
        options: undefined,
        value: '',
        conf: undefined,
      },
    ],
    destinations: [
      {
        id: 'destination_create',
        name: 'destination_create',
        type: 'fieldset',
        component: Fieldset,
        label: 'Create a destination',
        helper_text: undefined,
        options: undefined,
        value: [],
        conf: {
          type: 'confSelect',
          title: 'Destinations',
          description:
            'Every study needs a destination, where do the recruitment ads send the users?',
          selector: {
            name: 'destination_type',
            type: 'select',
            label: 'Destination type',
            options: [messenger, web, app],
          },
        },
      },
      {
        id: 'name',
        name: 'name',
        type: 'text',
        component: Text,
        label: 'Give your destination a name',
        helper_text: 'E.g example-fly-1',
        options: undefined,
        value: '',
        conf: undefined,
      },
      {
        id: 'add_destination',
        name: 'add_destination',
        type: 'button',
        component: Button,
        label: 'Add destination',
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: undefined,
      },
    ],
    simple_list: [
      {
        id: 'foo',
        name: 'foo',
        type: 'text',
        component: Text,
        label: 'I am a list item',
        helper_text: 'Foo',
        options: undefined,
        value: '',
        conf: undefined,
      },
    ],
  },
];

export default initialState;