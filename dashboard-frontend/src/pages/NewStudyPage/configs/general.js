import countries from '../../../fixtures/countries';

export const general = {
  type: 'config-object',
  title: 'General',
  description: 'The "general" configuration consists of... General stuff?',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helpertext: 'E.g example-fly-conf',
    },
    {
      name: 'objective',
      type: 'select',
      label: 'Objective',
      defaultValue: 'Select an objective',
      options: [
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
      defaultValue: 'Select an optimization goal',
      options: [
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
      helpertext: 'E.g 1855355231229529',
    },
    {
      name: 'min_budget',
      type: 'number',
      label: 'Minimum Budget',
      helpertext: 'E.g 10',
    },
    {
      name: 'opt_window',
      type: 'number',
      label: 'Opt-in window',
      helpertext: 'E.g 48',
    },
    {
      name: 'instagram_id',
      type: 'number',
      label: 'Instagram ID',
      helpertext: 'E.g 2327764173962588',
    },
    {
      name: 'ad_account',
      type: 'number',
      label: 'Ad account',
      helpertext: 'E.g 1342820622846299',
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
