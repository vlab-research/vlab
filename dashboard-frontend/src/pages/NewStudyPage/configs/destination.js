export const destination = {
  configType: 'destination',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
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
