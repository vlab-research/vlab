export const web = {
  type: 'configObject',
  title: 'Web',
  description: 'Web...',
  key: 'name',
  fields: [
    {
      name: 'name',
      type: 'text',
      label: 'Survey name',
      helper_text: 'E.g Malaria study',
    },
    {
      name: 'url_template',
      type: 'text',
      label: 'Url template',
      helper_text: 'E.g https://survey.typeform.com/to/Wm94iUUB',
    },
  ],
};
