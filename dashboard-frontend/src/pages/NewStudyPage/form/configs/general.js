import countries from '../../../../fixtures/countries';

export const general = {
  type: 'configObject',
  title: 'General',
  description: 'The "general" configuration consists of... General stuff?',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helper_text: 'E.g example-fly-conf',
    },
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
          name: 'messages',
          label: 'Messages',
        },
        {
          name: 'objective_2',
          label: 'Objective 2',
        },
        {
          name: 'objective_3',
          label: 'Objective 3',
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
          name: 'link_clicks',
          label: 'Link clicks',
        },
        {
          name: 'optimization_goal_2',
          label: 'Optimization goal 2',
        },
        {
          name: 'optimization_goal_3',
          label: 'Optimization goal 3',
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
      type: 'number',
      label: 'Page ID',
      helper_text: 'E.g 1855355231229529',
    },
    {
      name: 'min_budget',
      type: 'number',
      label: 'Minimum Budget',
      helper_text: 'E.g 10',
    },
    {
      name: 'opt_window',
      type: 'number',
      label: 'Opt-in window',
      helper_text: 'E.g 48',
    },
    {
      name: 'instagram_id',
      type: 'number',
      label: 'Instagram ID',
      helper_text: 'E.g 2327764173962588',
    },
    {
      name: 'ad_account',
      type: 'number',
      label: 'Ad account',
      helper_text: 'E.g 1342820622846299',
    },
    {
      name: 'country',
      type: 'select',
      label: 'Country',
      defaultValue: 'Select a country',
      options: countries,
    },
  ],
};
