import countries from '../../fixtures/countries.json';

export const general = {
  configType: 'general',
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
      label: 'Optimization Goal',
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
      label: 'Destination Type',
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
      type: 'text',
      label: 'Page ID',
      helpertext: 'E.g 1855355231229529',
    },
    {
      name: 'min_budget',
      type: 'text',
      label: 'Minimum Budget',
      helpertext: 'E.g 10',
    },
    {
      name: 'opt_window',
      type: 'text',
      label: 'Optional Window',
      helpertext: 'E.g 48',
    },
    {
      name: 'instagram_id',
      type: 'text',
      label: 'Instagram ID',
      helpertext: 'E.g 2327764173962588',
    },
    {
      name: 'ad_account',
      type: 'text',
      label: 'Ad Account',
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
