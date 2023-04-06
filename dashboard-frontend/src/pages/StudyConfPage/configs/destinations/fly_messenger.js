export const fly_messenger = {
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
      name: 'survey_name',
      type: 'text',
      label: 'Survey Name',
      helper_text: 'Eg. Fly',
    },
  ],
};

export default fly_messenger;
