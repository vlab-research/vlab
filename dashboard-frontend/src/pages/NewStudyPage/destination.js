export const destination = {
  configType: 'destination',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Name',
    },
    {
      name: 'initial_shortcode',
      type: 'text',
      label: 'Initial shortcode',
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
