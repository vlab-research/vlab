export const messenger = {
  type: 'confObject',
  title: 'Fly Messenger',
  description: 'Fly...',
  key: 'intial_shortcode',
  fields: [
    {
      name: 'initial_shortcode',
      type: 'text',
      label: 'Initial shortcode',
      helper_text: 'E.g 12345',
    },
    {
      name: 'name',
      type: 'text',
      label: 'Survey Name',
      helper_text: 'Eg. vlab-vaping',
    },
  ],
};
