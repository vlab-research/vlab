export const fly_messenger_destination = {
  type: 'config-object',
  title: 'Fly Messenger',
  description: 'Fly...',
  key: 'intial_shortcode', // tells us which field can be used as a unique key
  fields: [
    {
      name: 'initial_shortcode',
      type: 'text',
      label: 'Initial shortcode',
      helpertext: 'E.g 12345',
    },
    {
      name: 'survey_name',
      type: 'text',
      label: 'Survey Name',
      helpertext: 'Eg. Fly',
    },
  ],
};
