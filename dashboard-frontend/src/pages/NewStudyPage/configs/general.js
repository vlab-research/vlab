import countries from '../../../fixtures/countries.json';

export const general = {
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
      options: [
        {
          name: 'Messages',
        },
        {
          name: 'objective 2',
        },
        {
          name: 'objective 3',
        },
      ],
    },
    {
      name: 'optimization_goal',
      type: 'select',
      label: 'Optimization goal',
      options: [
        {
          name: 'Link clicks',
        },
        {
          name: 'optimization goal 2',
        },
        {
          name: 'optimization goal 3',
        },
      ],
    },
    {
      name: 'destination_type',
      type: 'select',
      label: 'Destination type',
      options: [
        {
          name: 'Web',
        },
        {
          name: 'Messenger',
        },
        {
          name: 'App',
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
      label: 'Optional window',
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
      options: countries,
    },
  ],
};