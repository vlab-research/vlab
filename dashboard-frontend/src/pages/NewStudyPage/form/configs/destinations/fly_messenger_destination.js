export const fly_messenger_destination = {
  type: 'configObject',
  title: 'Fly Messenger',
  description: 'Fly...',
  key: 'intial_shortcode', // tells us which field can be used as a unique key
  fields: [
    {
      name: 'initial_shortcode',
      type: 'text',
      label: 'Initial shortcode',
      helper_text: 'E.g 12345',
    },
    {
      name: 'survey_name',
      type: 'text',
      label: 'Survey Name',
      helper_text: 'Eg. Fly',
    },
  ],
};
