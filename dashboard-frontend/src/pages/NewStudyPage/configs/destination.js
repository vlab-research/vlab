export const destination = {
  configType: 'destination',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Name',
      helpertext: 'E.g fly',
    },
    {
      name: 'initial_shortcode',
      type: 'text',
      label: 'Initial shortcode',
      helpertext: 'E.g vapingpregate',
    },
    {
      name: 'destination',
      type: 'select',
      label: 'Destination',
      options: [
        {
          name: 'Web',
        },
        {
          name: 'Messenger Survey',
        },
        {
          name: 'App',
        },
      ],
    },
  ],
};
